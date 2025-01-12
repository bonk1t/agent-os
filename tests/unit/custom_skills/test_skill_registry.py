from pathlib import Path
from unittest.mock import Mock, patch

from agency_swarm import BaseTool
from agency_swarm.tools import CodeInterpreter, Retrieval

from backend.custom_skills.skill_registry import SkillRegistry


def test_skill_registry_initialization():
    with patch.object(SkillRegistry, "_load_custom_skills"):  # Mock _load_custom_skills to do nothing
        registry = SkillRegistry()
        assert registry._skills == {
            "CodeInterpreter": CodeInterpreter,
            "Retrieval": Retrieval,
        }


def test_load_custom_skills():
    registry = SkillRegistry()

    # Create mock skill class
    class MockSkill(BaseTool):
        def run(self):
            pass

    mock_module = Mock()
    mock_module.MockSkill = MockSkill

    with patch.object(registry, "_import_module_from_file", return_value=mock_module):
        registry._load_custom_skills()
        assert "MockSkill" in registry._skills
        assert registry._skills["MockSkill"] == MockSkill


def test_import_module_from_file():
    registry = SkillRegistry()

    # Test invalid module
    result = registry._import_module_from_file(Path("nonexistent.py"))
    assert result is None

    # Test valid module
    with patch("importlib.util.spec_from_file_location") as mock_spec:
        mock_spec.return_value = Mock(loader=Mock())
        result = registry._import_module_from_file(Path("valid.py"))
        assert result is not None


def test_get_skill():
    registry = SkillRegistry()

    # Test getting existing skill
    class MockSkill(BaseTool):
        def run(self):
            pass

    registry.register_skill("MockSkill", MockSkill)
    result = registry.get_skill("MockSkill")
    assert result == MockSkill

    # Test getting non-existent skill
    result = registry.get_skill("NonExistentSkill")
    assert result is None


def test_register_and_is_registered():
    registry = SkillRegistry()

    class MockSkill(BaseTool):
        def run(self):
            pass

    registry.register_skill("MockSkill", MockSkill)
    assert registry.is_registered("MockSkill")
    assert not registry.is_registered("NonExistentSkill")


def test_get_all_skills():
    registry = SkillRegistry()

    class MockSkill(BaseTool):
        def run(self):
            pass

    registry.register_skill("MockSkill", MockSkill)
    skills = registry.get_all_skills()
    assert "MockSkill" in skills
    assert skills["MockSkill"] == MockSkill
