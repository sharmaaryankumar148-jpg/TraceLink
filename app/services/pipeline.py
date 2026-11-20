import logging

from sqlalchemy.orm import Session

from app import cache
from app.models import Complaint, Identifier
from app.services import extractor, linker, llm
from app.services.classifier import classifier
from app.services.urgency import score_urgency

log = logging.getLogger(__name__)


def process_complaint(db: Session, complaint_id: int) -> Complaint | None:
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        log.error("Complaint %s not found", complaint_id)
        return None

    try:
        found = extractor.extract(complaint.text)
        complaint.identifiers = [Identifier(kind=k, value=v) for k, v in found.identifiers()]
        complaint.amount_involved = found.total_amount
        db.flush()  # identifiers need to be in the db before linking

        complaint.category, complaint.category_confidence = classifier.predict(complaint.text)

        linked = linker.direct_links(db, complaint.id)
        complaint.urgency_score, complaint.urgency_level, complaint.urgency_reasons = score_urgency(
            complaint.category, complaint.text, found.total_amount, len(linked)
        )

        complaint.llm_details = llm.enrich(complaint.text)
        complaint.status = "processed"
        db.commit()
    except Exception:
        db.rollback()
        log.exception("Processing failed for complaint %s", complaint_id)
        complaint = db.get(Complaint, complaint_id)
        complaint.status = "failed"
        db.commit()

    cache.invalidate_stats()
    return complaint
