from pydantic import BaseModel, Field


class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class Item(ItemCreate):
    id: str
    owner_uid: str
