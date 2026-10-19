from pydantic import BaseModel, EmailStr


class Credentials(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str | None = None


class TokenOut(BaseModel):
    access_token: str
    user: UserOut
