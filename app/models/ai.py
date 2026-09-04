from typing import Literal

from pydantic import BaseModel, Field

Role = Literal["user", "assistant"]


class ChatMessage(BaseModel):
    role: Role
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)
    max_tokens: int = Field(default=1024, ge=1, le=8192)


class ChatResponse(BaseModel):
    reply: str
    model: str
