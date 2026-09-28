from pydantic import BaseModel, Field


class PushTokenCreate(BaseModel):
    token: str = Field(min_length=20)
    platform: str = Field(min_length=1, max_length=30)
    owner_id: str | None = None
