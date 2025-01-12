import importlib.util
from pathlib import Path

from agency_swarm import BaseTool
from agency_swarm.tools import CodeInterpreter, Retrieval

from backend.repositories.skill_config_storage import SkillConfigStorage
from backend.services.skill_manager import SkillManager


class SkillRegistry:
    """Proxy class for managing skill registration and validation."""

    def __init__(self):
        # Map of skill names to skill classes
        self._skills = {
            "CodeInterpreter": CodeInterpreter,
            "Retrieval": Retrieval,
        }
        self._load_custom_skills()

    def _load_custom_skills(self) -> None:
        """Load all custom skills from the directory."""
        current_dir = Path(__file__).parent

        for file_path in current_dir.glob("*.py"):
            if file_path.name == "__init__.py" or file_path.name == "skill_registry.py":
                continue

            module = self._import_module_from_file(file_path)
            if module is None:
                continue

            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, BaseTool) and attr != BaseTool:
                    self._skills[attr_name] = attr

    def _import_module_from_file(self, file_path: Path):
        """Import a module from file path."""
        module_name = file_path.stem
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
            return module
        except Exception:
            return None

    def reload(self) -> None:
        """Reload all skills."""
        self._skills = {
            "CodeInterpreter": CodeInterpreter,
            "Retrieval": Retrieval,
        }
        self._load_custom_skills()

    def get_skill(self, name: str) -> type[BaseTool] | None:
        """Get a skill by name. If not found locally, try to fetch from database."""
        skill_class = self._get_skill_from_registry(name)
        if skill_class is None:
            skill_class = self._get_skill_from_database(name)
        return skill_class

    def _get_skill_from_registry(self, name: str) -> type[BaseTool] | None:
        """Retrieve a skill from the local registry."""
        return self._skills.get(name)

    def _get_skill_from_database(self, name: str) -> type[BaseTool] | None:
        """Retrieve a skill from the database and register it locally if found."""
        self.storage = SkillConfigStorage()
        self.skill_manager = SkillManager(self.storage)
        skill_configs = self.storage.load_by_titles([name])
        skill_config = skill_configs[0] if skill_configs else None
        if skill_config:
            self.skill_manager._save_skill_to_file(skill_config)
            self.reload()
            return self._get_skill_from_registry(name)
        return None

    def register_skill(self, name: str, skill: type[BaseTool]) -> None:
        """Register a new skill."""
        self._skills[name] = skill

    def is_registered(self, name: str) -> bool:
        """Check if a skill is registered by name."""
        return name in self._skills

    def get_all_skills(self) -> dict[str, type[BaseTool]]:
        """Get all registered skills."""
        return self._skills.copy()


# Create a global instance of the registry
skill_registry = SkillRegistry()
