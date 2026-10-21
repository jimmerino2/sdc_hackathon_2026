from pydantic import BaseModel, Field


class SkillScore(BaseModel):
    """A skill found in the resume and how strongly the resume shows it."""

    name: str = Field(description="O*NET skill name")
    score: float = Field(
        ge=0, le=1,
        description="How strongly the resume evidences the skill, 0-1 (OpenJev: probability; gateway model: its own rating). "
        "It is evidence strength, not a measured proficiency level",
    )


class Engine(BaseModel):
    """Which engine read the skills, and how it did. Handy for comparing OpenJev with the gateway model."""

    source: str | None = Field(None, description="'openjev' or 'llm'; null if the skills step did not run")
    model: str | None = Field(None, description="'openjev', or the gateway model name")
    candidates: int | None = Field(None, description="How many candidate skills the engine considered (after the keyword filter)")
    seconds: float | None = Field(None, description="Time the skills step took, excluding PDF reading")


class ResumeOut(BaseModel):
    """Result of reading an uploaded resume."""

    filename: str | None = Field(None, description="Name of the uploaded file")
    page_count: int = Field(description="Number of pages in the PDF")
    char_count: int = Field(description="Length of the extracted text; 0 usually means a scanned PDF")
    top_skills: list[SkillScore] | None = Field(None, description="The 5 strongest skills, strongest first")
    skills: list[SkillScore] | None = Field(None, description="Every skill found, strongest first")
    error: str | None = Field(None, description="Why skills is null, when the PDF was read but the skills step did not run")
    engine: Engine
