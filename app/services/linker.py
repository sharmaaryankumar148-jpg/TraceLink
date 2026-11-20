from collections import deque

from sqlalchemy import func, select, tuple_
from sqlalchemy.orm import Session

from app.models import Complaint, Identifier

MAX_NETWORK_SIZE = 200


def _identifiers_of(db: Session, complaint_ids: list[int]) -> list[tuple[int, str, str]]:
    rows = db.execute(
        select(Identifier.complaint_id, Identifier.kind, Identifier.value).where(
            Identifier.complaint_id.in_(complaint_ids)
        )
    )
    return [tuple(r) for r in rows]


def _complaints_with(db: Session, pairs: set[tuple[str, str]]) -> list[tuple[int, str, str]]:
    if not pairs:
        return []
    rows = db.execute(
        select(Identifier.complaint_id, Identifier.kind, Identifier.value).where(
            tuple_(Identifier.kind, Identifier.value).in_(list(pairs))
        )
    )
    return [tuple(r) for r in rows]


def direct_links(db: Session, complaint_id: int) -> dict[int, list[dict]]:
    own = {(kind, value) for _, kind, value in _identifiers_of(db, [complaint_id])}
    links: dict[int, list[dict]] = {}
    for other_id, kind, value in _complaints_with(db, own):
        if other_id != complaint_id:
            links.setdefault(other_id, []).append({"kind": kind, "value": value})
    return links


def network(db: Session, complaint_id: int) -> dict:
    # BFS: A-C share a phone, A-B share a UPI id -> A, B, C are one network
    visited_complaints = {complaint_id}
    visited_identifiers: set[tuple[str, str]] = set()
    edges: list[dict] = []
    queue = deque([complaint_id])

    while queue and len(visited_complaints) < MAX_NETWORK_SIZE:
        current = queue.popleft()
        new_pairs = {
            (kind, value)
            for _, kind, value in _identifiers_of(db, [current])
            if (kind, value) not in visited_identifiers
        }
        visited_identifiers |= new_pairs
        for other_id, kind, value in _complaints_with(db, new_pairs):
            if other_id == current:
                continue
            edges.append({"from": current, "to": other_id, "kind": kind, "value": value})
            if other_id not in visited_complaints:
                visited_complaints.add(other_id)
                queue.append(other_id)

    complaints = db.scalars(select(Complaint).where(Complaint.id.in_(visited_complaints))).all()
    return {
        "root_complaint_id": complaint_id,
        "complaint_ids": sorted(visited_complaints),
        "complaint_count": len(visited_complaints),
        "total_amount_involved": sum(c.amount_involved or 0 for c in complaints),
        "areas": sorted({c.area for c in complaints if c.area}),
        "shared_identifiers": sorted(
            {(e["kind"], e["value"]) for e in edges}, key=lambda p: (p[0], p[1])
        ),
        "edges": edges,
    }


def repeat_identifiers(db: Session, min_complaints: int = 2, limit: int = 20) -> list[dict]:
    count = func.count(func.distinct(Identifier.complaint_id))
    rows = db.execute(
        select(Identifier.kind, Identifier.value, count.label("n"))
        .group_by(Identifier.kind, Identifier.value)
        .having(count >= min_complaints)
        .order_by(count.desc())
        .limit(limit)
    ).all()

    results = []
    for kind, value, n in rows:
        ids = db.scalars(
            select(Identifier.complaint_id).where(Identifier.kind == kind, Identifier.value == value).distinct()
        ).all()
        complaints = db.scalars(select(Complaint).where(Complaint.id.in_(ids))).all()
        results.append(
            {
                "kind": kind,
                "value": value,
                "complaint_count": n,
                "complaint_ids": sorted(ids),
                "total_amount_involved": sum(c.amount_involved or 0 for c in complaints),
                "areas": sorted({c.area for c in complaints if c.area}),
            }
        )
    return results
