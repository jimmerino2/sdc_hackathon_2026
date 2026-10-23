from pydantic import BaseModel, Field


class SdgWeight(BaseModel):
    sdg: int = Field(ge=1, le=17, description="UN Sustainable Development Goal number")
    value: float = Field(ge=0, le=1, description="How much the interest serves that goal; one interest's values add up to 1")


class Interest(BaseModel):
    id: int
    interest: str
    description: str
    icon: str = Field(description="Lucide icon name, e.g. 'chef-hat'")
    sdg: list[SdgWeight]


class SdgFocus(BaseModel):
    """One goal in a learner's SDG focus, worked out from the interests they picked."""

    sdg: int = Field(ge=1, le=17)
    name: str = Field(description="The goal's name, e.g. 'Zero Hunger'")
    value: float = Field(ge=0, le=1, description="Share of the learner's interests that point at this goal; all goals add up to 1")
