from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import cache
from app.db import get_db
from app.models import Complaint, Identifier, User
from app.schemas import ComplaintDetail, ComplaintIn, ComplaintSummary, LinkedComplaint
from app.security import audit, get_current_user
from app.services import extractor, linker
from app.services.pipeline import process_complaint

router = APIRouter(prefix="/complaints", tags=["complaints"])


def _detail(db: Session, complaint: Complaint) -> ComplaintDetail:
    detail = ComplaintDetail.model_validate(complaint)
    if complaint.status == "processed":
        detail.linked_complaints = [
            LinkedComplaint(complaint_id=cid, shared=shared)
            for cid, shared in sorted(linker.direct_links(db, complaint.id).items())
        ]
    return detail


@router.post("", response_model=ComplaintDetail, status_code=status.HTTP_201_CREATED)
def submit_complaint(
    body: ComplaintIn,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """201 with results when processed inline, 202 + `queued` when sent to the redis worker."""
    complaint = Complaint(text=body.text, area=body.area, status="queued", submitted_by=user.id)
    db.add(complaint)
    db.commit()
    audit(db, user, "submit_complaint", f"complaint:{complaint.id}")

    if cache.enqueue(complaint.id):
        response.status_code = status.HTTP_202_ACCEPTED
    else:
        complaint = process_complaint(db, complaint.id)
    db.refresh(complaint)
    return _detail(db, complaint)


@router.get("", response_model=list[ComplaintSummary])
def list_complaints(
    category: str | None = None,
    urgency_level: str | None = Query(default=None, pattern="^(low|medium|high)$"),
    area: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Most urgent first."""
    query = select(Complaint)
    if category:
        query = query.where(Complaint.category == category)
    if urgency_level:
        query = query.where(Complaint.urgency_level == urgency_level)
    if area:
        query = query.where(Complaint.area == area)
    query = query.order_by(Complaint.urgency_score.desc().nulls_last(), Complaint.created_at.desc())
    audit(db, user, "list_complaints")
    return db.scalars(query.offset(offset).limit(limit)).all()


@router.get("/search", response_model=list[ComplaintSummary])
def search_by_identifier(
    value: str = Query(min_length=3, description="Phone, UPI ID, account no., email or URL"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    found = extractor.extract(value)
    values = [v for _, v in found.identifiers()] or [value.strip().lower()]
    ids = db.scalars(select(Identifier.complaint_id).where(Identifier.value.in_(values)).distinct()).all()
    audit(db, user, "search_identifier", value)
    return db.scalars(select(Complaint).where(Complaint.id.in_(ids)).order_by(Complaint.created_at)).all()


@router.get("/{complaint_id}", response_model=ComplaintDetail)
def get_complaint(complaint_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    audit(db, user, "view_complaint", f"complaint:{complaint_id}")
    return _detail(db, complaint)


@router.get("/{complaint_id}/network")
def get_network(complaint_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if db.get(Complaint, complaint_id) is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    audit(db, user, "view_network", f"complaint:{complaint_id}")
    return linker.network(db, complaint_id)
