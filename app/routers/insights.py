from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import cache
from app.db import get_db
from app.models import AuditLog, Complaint, User
from app.schemas import AuditOut
from app.security import audit, require_role
from app.services import linker

router = APIRouter(tags=["supervisor"])


def _compute_stats(db: Session) -> dict:
    def counts(column):
        rows = db.execute(select(column, func.count()).group_by(column)).all()
        return {str(k): n for k, n in rows if k is not None}

    return {
        "total_complaints": db.scalar(select(func.count()).select_from(Complaint)),
        "by_category": counts(Complaint.category),
        "by_urgency": counts(Complaint.urgency_level),
        "by_status": counts(Complaint.status),
        "by_area": counts(Complaint.area),
        "total_amount_involved": db.scalar(select(func.coalesce(func.sum(Complaint.amount_involved), 0))),
        "repeat_identifiers": linker.repeat_identifiers(db),
    }


@router.get("/stats")
def stats(db: Session = Depends(get_db), user: User = Depends(require_role("supervisor"))):
    audit(db, user, "view_stats")
    cached = cache.get_cached_stats()
    if cached is not None:
        return {**cached, "cached": True}
    result = _compute_stats(db)
    cache.set_cached_stats(result)
    return {**result, "cached": False}


@router.get("/audit", response_model=list[AuditOut])
def audit_log(
    username: str | None = None,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("supervisor")),
):
    query = select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)
    if username:
        query = query.where(AuditLog.username == username)
    return db.scalars(query).all()
