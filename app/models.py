from datetime import date
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field

Role = Literal["viewer", "analyst", "administrator"]


class User(BaseModel):
    id: str
    role: Role
    departments: list[str]


class Document(BaseModel):
    id: str
    title: str
    department: str
    document_type: str
    access_level: Literal["internal", "restricted"]
    created_date: date
    text: str = Field(max_length=12000)
    root_cause: str | None = None


class ChatRequest(BaseModel):
    session_id: UUID
    message: str = Field(min_length=1, max_length=2000)
    department: str | None = Field(default=None, max_length=80)
    since: date | None = None
    until: date | None = None


class Answer(BaseModel):
    text: str = Field(min_length=1, max_length=12000)
    citations: list[str] = Field(default_factory=list, max_length=20)
