# TraceLink

Triage and linking API for cyber fraud complaints.

Complaints come in as free text (English / Hindi / Hinglish). TraceLink classifies each one,
pulls out the phone numbers, UPI IDs, bank accounts, emails, URLs and amounts, gives it an
urgency score with reasons, and links it to other complaints that share any of those
identifiers. So the same scammer showing up in complaints from different areas gets caught
as one network instead of separate cases.

Note: this is a prototype trained on synthetic data. Scores and links are leads for an
officer to check, not decisions.

## Example

| # | Area | Complaint |
|---|---|---|
| 1 | Rohini | Call from 9876543210 about a KBC lottery, paid Rs 15,000 to lucky.kbc@ybl |
| 2 | Dwarka | "Job offer aaya, Rs 8,500 registration fee lucky.kbc@ybl pe bhej diya" |
| 3 | Laxmi Nagar | Threat to leak morphed photos unless Rs 50,000 is paid, calls from +91 98765 43210 |

Output:

```
#1 lottery_scam  urgency 32  low    linked: 2, 3
#2 job_scam      urgency 30  low    linked: 1
#3 sextortion    urgency 100 high   linked: 1
   reasons: threat to the victim, intimate images involved, amount involved ₹50,000,
            linked to 1 other complaint(s): possible repeat offender

GET /complaints/3/network  ->  [1, 2, 3], ₹73,500 total, Dwarka / Laxmi Nagar / Rohini

GET /stats  repeat identifiers:
   9876543210     2 complaints  ₹65,000
   lucky.kbc@ybl  2 complaints  ₹23,500
```

Complaint 3 doesn't share anything with complaint 2 directly, they're connected through 1.

## How it works

- **Extraction** - regex, runs offline. Values are normalised so `+91 98765-43210` and
  `9876543210` match. Account numbers need "account"/"a/c" before them, UPI ids are kept
  separate from emails.
- **Classification** - scikit-learn, TF-IDF on character n-grams + logistic regression.
  Char n-grams deal with Hinglish and spelling mistakes better than words.
  Categories: upi_fraud, lottery_scam, job_scam, investment_scam, sextortion,
  account_hacking, phishing.
- **Urgency** - rule based (threats, self harm, intimate images, minors, recent fraud,
  remote access apps, amount, repeat offender) so every score has reasons attached.
- **Linking** - direct links through shared identifiers, and BFS for the full network.
- **Redis** - job queue (`LPUSH`/`BRPOP`) processed by `worker.py`, and a cache for `/stats`.
  Without redis everything is processed inline.
- **Auth** - JWT, two roles (officer, supervisor), PBKDF2 password hashing, no public signup,
  audit log of who submitted / viewed / searched what.
- **LLM (optional)** - Gemini pulls names, places and a summary into a pydantic schema.
  Off unless `GEMINI_API_KEY` is set.

```
client --JWT--> FastAPI (/auth /complaints /stats /audit) ---> SQLite/Postgres
                    |
                    | QUEUE_MODE=redis
                    v
              redis queue ---> worker.py: extract -> classify -> link -> urgency -> (llm)
```

```
app/
  main.py, config.py, db.py, models.py, schemas.py
  security.py      hashing, jwt, roles, audit
  cache.py         redis queue + stats cache
  routers/         auth, complaints, insights
  services/        extractor, classifier, urgency, linker, llm, pipeline
worker.py
ml/                synthetic data generator, training
tests/
```

## Running

```bash
python -m venv .venv
.venv\Scripts\activate        # linux/mac: source .venv/bin/activate
pip install -r requirements.txt
python -m ml.train
uvicorn app.main:app --reload
```

Go to http://127.0.0.1:8000/docs, click Authorize and log in with `admin` / `admin123`
(set your own in `.env`, see `.env.example`).

With the redis queue (`QUEUE_MODE=redis` in `.env`), in three terminals:

```bash
python scripts/dev_redis.py   # or a real redis server
uvicorn app.main:app
python worker.py
```

Docker: `docker compose up --build` (haven't tested the compose file yet)

Tests: `pytest`

## Endpoints

| Method | Path | Role | |
|---|---|---|---|
| POST | /auth/login | - | get token |
| POST | /auth/users | supervisor | create account |
| POST | /complaints | officer | submit (201 processed / 202 queued) |
| GET | /complaints | officer | triage queue, most urgent first |
| GET | /complaints/{id} | officer | result + linked complaints |
| GET | /complaints/{id}/network | officer | full connected network |
| GET | /complaints/search?value= | officer | complaints mentioning a phone/UPI/account |
| GET | /stats | supervisor | counts + repeat identifiers (cached) |
| GET | /audit | supervisor | audit log |

## Model results

Dataset is synthetic: 210 complaints from 35 templates (5 per category). A normal random
split gives 100% because test sentences are the same templates as training, so `ml/train.py`
holds out one full template per category instead.

| Split | Accuracy | Macro F1 |
|---|---|---|
| held-out templates | 0.64 | 0.56 |

Needs real labelled data to get a meaningful number. Any csv with `text,category` works:
`python -m ml.train data.csv`

## TODO

- [x] extraction, classification, urgency, linking, stats
- [x] training script with held-out evaluation
- [x] redis queue + worker, stats cache, JWT roles, audit log
- [ ] train on a real cybercrime complaint dataset
- [ ] re-score older complaints when new links show up
- [ ] Devanagari Hindi
- [ ] local LLM (ollama) instead of Gemini
- [ ] mask personal data in logs, postgres, rate limiting
- [ ] dashboard + area hotspot map
