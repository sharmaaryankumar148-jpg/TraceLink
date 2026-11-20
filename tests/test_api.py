import fakeredis

from app import cache

A = "I got a call from 9876543210 saying I won KBC lottery. I paid Rs 15,000 processing fee to lucky.kbc@ybl."
B = "Job offer on WhatsApp, Rs 8,500 registration fee bheja lucky.kbc@ybl pe, ab number band hai."
C = "Someone is threatening to leak my morphed photos unless I pay Rs 50,000. He calls from +91 98765 43210."
UNRELATED = "My Instagram account was hacked after I shared OTP with 9000011111. Hacker asks friends for money."


def submit(client, headers, text, area):
    r = client.post("/complaints", json={"text": text, "area": area}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_requires_login(client):
    assert client.get("/complaints").status_code == 401
    assert client.post("/complaints", json={"text": A}).status_code == 401


def test_wrong_password(client):
    r = client.post("/auth/login", data={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


def test_complaint_is_processed(client, officer_headers):
    body = submit(client, officer_headers, A, "Rohini")
    assert body["status"] == "processed"
    assert body["category"]
    assert 0 <= body["category_confidence"] <= 1
    assert {"kind": "phone", "value": "9876543210"} in body["identifiers"]
    assert {"kind": "upi", "value": "lucky.kbc@ybl"} in body["identifiers"]
    assert body["amount_involved"] == 15000
    assert body["urgency_reasons"]


def test_linking_and_network(client, officer_headers):
    a = submit(client, officer_headers, A, "Rohini")
    b = submit(client, officer_headers, B, "Dwarka")
    submit(client, officer_headers, UNRELATED, "Saket")
    c = submit(client, officer_headers, C, "Laxmi Nagar")

    assert [link["complaint_id"] for link in c["linked_complaints"]] == [a["id"]]
    assert c["urgency_level"] == "high"

    # B only connects to C through A
    net = client.get(f"/complaints/{c['id']}/network", headers=officer_headers).json()
    assert net["complaint_ids"] == sorted([a["id"], b["id"], c["id"]])
    assert net["total_amount_involved"] == 15000 + 8500 + 50000
    assert net["areas"] == ["Dwarka", "Laxmi Nagar", "Rohini"]

    found = client.get("/complaints/search", params={"value": "+91-98765-43210"}, headers=officer_headers).json()
    assert sorted(x["id"] for x in found) == sorted([a["id"], c["id"]])


def test_triage_queue_sorted_by_urgency(client, officer_headers):
    submit(client, officer_headers, A, "Rohini")
    submit(client, officer_headers, C, "Laxmi Nagar")
    queue = client.get("/complaints", headers=officer_headers).json()
    scores = [x["urgency_score"] for x in queue]
    assert scores == sorted(scores, reverse=True)


def test_roles_and_audit(client, admin_headers, officer_headers):
    complaint = submit(client, officer_headers, A, "Rohini")
    client.get(f"/complaints/{complaint['id']}", headers=officer_headers)

    assert client.get("/stats", headers=officer_headers).status_code == 403
    assert client.get("/audit", headers=officer_headers).status_code == 403
    r = client.post("/auth/users", json={"username": "x" * 5, "password": "y" * 8}, headers=officer_headers)
    assert r.status_code == 403

    log = client.get("/audit", params={"username": "officer1"}, headers=admin_headers).json()
    actions = [entry["action"] for entry in log]
    assert "submit_complaint" in actions and "view_complaint" in actions


def test_stats_repeat_identifiers(client, admin_headers, officer_headers):
    submit(client, officer_headers, A, "Rohini")
    submit(client, officer_headers, B, "Dwarka")
    stats = client.get("/stats", headers=admin_headers).json()
    assert stats["total_complaints"] == 2
    upi = next(x for x in stats["repeat_identifiers"] if x["value"] == "lucky.kbc@ybl")
    assert upi["complaint_count"] == 2
    assert upi["total_amount_involved"] == 23500


def test_redis_queue_worker_and_cache(client, admin_headers, officer_headers):
    from worker import process_next_job

    cache.set_client(fakeredis.FakeRedis(decode_responses=True))

    r = client.post("/complaints", json={"text": A, "area": "Rohini"}, headers=officer_headers)
    assert r.status_code == 202
    assert r.json()["status"] == "queued"
    assert cache.queue_length() == 1

    assert process_next_job(timeout=1) == r.json()["id"]
    assert cache.queue_length() == 0
    done = client.get(f"/complaints/{r.json()['id']}", headers=officer_headers).json()
    assert done["status"] == "processed"

    first = client.get("/stats", headers=admin_headers).json()
    second = client.get("/stats", headers=admin_headers).json()
    assert first["cached"] is False and second["cached"] is True
