from datetime import UTC, datetime

from pydantic import BaseModel, Field


class SkillConfig(BaseModel):
    """Skill configuration model, corresponds to the ISkill type in the frontend"""

    id: str | None = Field(None, description="Unique identifier for the configuration")
    user_id: str | None = Field(None, description="The user ID owning this configuration")
    title: str = Field(..., description="Name of the skill")
    description: str = Field("", description="Description of the skill")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(), description="Timestamp of the last update"
    )
    content: str = Field("", description="The actual code of the skill")
