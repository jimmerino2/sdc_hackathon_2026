from pydantic import BaseModel, EmailStr, Field


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72, description="At least 8 characters")


class UserOut(BaseModel):
    id: str
    email: str | None = None


class SessionOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int | None = None
    user: UserOut


class RegisterOut(BaseModel):
    user: UserOut
    session: SessionOut | None = Field(
        None, description="Null when the project requires email confirmation; confirm the email, then log in"
    )
    message: str
