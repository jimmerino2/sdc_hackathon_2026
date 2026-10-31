from pydantic import BaseModel, Field


class Programme(BaseModel):
    """An HRD Corp-claimable course that teaches a skill, from HRD Corp's public BizMatch course list."""

    course_id: int = Field(description="BizMatch's own id for the course")
    training_provider: str
    course_name: str
    scheme: str = Field(description="'HRD Corp Claimable Course' or 'e-LATiH'")
    certification: str | None = Field(None, description="'Attendance/Completion' or 'Professional Certification'")
    fee_rm: float = Field(description="Listed fee in RM, before the discount")
    discount_pct: float = Field(description="Discount on the listed fee, in percent")
    fee_after_discount_rm: float = Field(description="Fee in RM after the discount")
    in_house: bool = Field(description="True for a workshop a company books for its own staff, which an individual can't enrol in")
    fetched: str = Field(description="The day the list was read, YYYY-MM-DD; fees and discounts change")
    source_url: str = Field(description="The BizMatch list page the course was read from, sorted as it was read. The list has no page per course, so this opens the list")
