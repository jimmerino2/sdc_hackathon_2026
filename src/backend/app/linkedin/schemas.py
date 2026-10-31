from pydantic import BaseModel, Field


class Status(BaseModel):
    enabled: bool = Field(description="True when the LinkedIn app keys are set, so posting is available")


class ShareStart(BaseModel):
    text: str = Field(description="The post text, as the learner edited it (up to 3,000 characters)")
    image_base64: str = Field(description="The PNG to attach, base64-encoded (a data: URL prefix is accepted)")


class ShareStarted(BaseModel):
    authorize_url: str = Field(description="Send the browser here: LinkedIn asks the learner to sign in and allow one post")
