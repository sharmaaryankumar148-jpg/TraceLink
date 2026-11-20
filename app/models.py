from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(20), default="officer")  # officer | supervisor
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    area: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="queued")  # queued | processed | failed

    category: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    category_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    urgency_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    urgency_level: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    urgency_reasons: Mapped[list | None] = mapped_column(JSON, nullable=True)
    amount_involved: Mapped[float | None] = mapped_column(Float, nullable=True)
    llm_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    submitted_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    identifiers: Mapped[list["Identifier"]] = relationship(
        back_populates="complaint", cascade="all, delete-orphan"
    )


# one row per phone/upi/account found in a complaint, stored normalised,
# so linking is just a lookup on (kind, value)
class Identifier(Base):
    __tablename__ = "identifiers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # phone | upi | account | email | url
    value: Mapped[str] = mapped_column(String(300))

    complaint: Mapped[Complaint] = relationship(back_populates="identifiers")

    __table_args__ = (Index("ix_identifier_kind_value", "kind", "value"),)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    username: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(50))
    target: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
