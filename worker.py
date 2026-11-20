# Pulls complaint ids off the redis queue and processes them.
# Needs QUEUE_MODE=redis. Run more than one for parallel processing.
import logging
import signal
import time

import redis

from app import cache
from app.config import settings
from app.db import SessionLocal, init_db
from app.services.pipeline import process_complaint

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s worker: %(message)s")
log = logging.getLogger("worker")

_running = True


def _stop(*_):
    global _running
    log.info("Stopping after the current job...")
    _running = False


def process_next_job(timeout: int = 5) -> int | None:
    complaint_id = cache.dequeue(timeout=timeout)
    if complaint_id is None:
        return None
    with SessionLocal() as db:
        complaint = process_complaint(db, complaint_id)
        if complaint is not None:
            log.info(
                "complaint %s -> %s, urgency %s (%s)",
                complaint_id, complaint.category, complaint.urgency_score, complaint.status,
            )
    return complaint_id


def main() -> None:
    if settings.queue_mode != "redis" or cache.get_client() is None:
        raise SystemExit("Worker needs QUEUE_MODE=redis and a reachable REDIS_URL.")
    init_db()
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    log.info("Waiting for complaints on %s ...", settings.redis_url)
    while _running:
        try:
            process_next_job()
        except (redis.exceptions.TimeoutError, redis.exceptions.ConnectionError) as exc:
            log.warning("Redis problem (%s), retrying in 2s", exc)
            time.sleep(2)


if __name__ == "__main__":
    main()
