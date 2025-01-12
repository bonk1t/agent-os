from backend.custom_skills.skill_registry import skill_registry

# For backwards compatibility
SKILL_MAPPING = skill_registry.get_all_skills()
