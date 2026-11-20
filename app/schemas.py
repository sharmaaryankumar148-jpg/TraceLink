from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8)
    role: str = Field(default="officer", pattern="^(officer|supervisor)$")


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    role: str


class ComplaintIn(BaseModel):
    text: str = Field(min_length=10, max_length=10_000, description="Complaint text (English, Hindi or Hinglish)")
    area: str | None = Field(default=None, max_length=100, description="Police station / area, e.g. Rohini")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "I got a call from 9876543210 saying I won a KBC lottery. They asked me to pay "
                "Rs 15,000 processing fee to lucky.kbc@ybl. After paying they blocked me.",
                "area": "Rohini",
            }
        }
    )


class IdentifierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    kind: str
    value: str


class LinkedComplaint(BaseModel):
    complaint_id: int
    shared: list[IdentifierOut]


class ComplaintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    text: str
    area: str | None
    status: str
    category: str | None
    category_confidence: float | None
    urgency_score: int | None
    urgency_level: str | None
    urgency_reasons: list[str] | None
    amount_involved: float | None
    identifiers: list[IdentifierOut]
    llm_details: dict | None
    created_at: datetime


class ComplaintDetail(ComplaintOut):
    linked_complaints: list[LinkedComplaint] = []


class ComplaintSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    area: str | None
    status: str
    category: str | None
    urgency_score: int | None
    urgency_level: str | None
    amount_involved: float | None
    created_at: datetime


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    action: str
    target: str | None
    created_at: datetime
