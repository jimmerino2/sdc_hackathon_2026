from pydantic import BaseModel, Field


class SdgGoal(BaseModel):
    sdg: int = Field(ge=1, le=17, description="UN Sustainable Development Goal number")
    name: str = Field(description="The goal's name, e.g. 'Decent Work and Economic Growth'")


class SdgTarget(BaseModel):
    """One SDG target (a sub-goal), with how the work serves it."""

    code: str = Field(description="The UN target, e.g. '8.2' or '9.b'")
    sdg: int = Field(ge=1, le=17, description="The goal the target belongs to")
    text: str = Field(description="How the work serves it, e.g. 'productivity through market innovation and commercialization'")


class SkillSdg(BaseModel):
    """The SDGs one of a role's skills serves (onet_skills_sdg)."""

    skill_id: str = Field(description="O*NET element id, as onet_role_skills.skill_id")
    skill_name: str
    skill_type: str = Field(description="'skill', 'knowledge' or 'tech'")
    main: SdgGoal
    relevant: list[SdgGoal]
    targets: list[SdgTarget]


class RoleGoal(BaseModel):
    """The measurable goal a role could work towards (onet_roles_sustainable_goals.csv)."""

    sdg: int | None = Field(default=None, ge=1, le=17, description="The goal the statement serves")
    text: str = Field(description="The goal statement, e.g. 'Reduce transit delays by 20% by 2027'")


class RoleSdg(BaseModel):
    """The SDGs and targets a role's work serves (onet_roles_sdg), and those of each of its skills."""

    onet_code: str
    main: SdgGoal = Field(description="The goal the role serves most")
    relevant: list[SdgGoal] = Field(description="The other goals it serves")
    targets: list[SdgTarget] = Field(description="The targets behind those goals, main goal's first")
    goal: RoleGoal | None = Field(default=None, description="A measurable goal for the role, if one is on record")
    skills: list[SkillSdg] = Field(description="Each of the role's O*NET skills, knowledge areas and tools that has SDGs on record")
