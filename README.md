# Payment Webhook Delivery Engine

A production-style webhook delivery system built with Python — accepts payment events, queues them reliably, and delivers to subscriber endpoints with retry logic, signature verification, and a live monitoring dashboard.

---

## Tech Stack

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?logo=fastapi)
![Celery](https://img.shields.io/badge/Celery-5.3-brightgreen)
![Redis](https://img.shields.io/badge/Redis-7.0-red?logo=redis)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker)
![pytest](https://img.shields.io/badge/tested_with-pytest-yellow)

---

## What It Does

In modern payment platforms (Stripe, Razorpay, etc.), webhooks are how transaction events get delivered to merchant systems. This project builds that delivery infrastructure from scratch:

- **Event ingestion** — Payment events (payment.success, payment.failed, payment.refunded) are submitted via a REST API
- **Reliable queuing** — Events are queued via Celery + Redis, decoupling ingestion from delivery
- **Subscriber delivery** — Events are delivered to registered HTTP endpoints with configurable retry logic
- **Retry with backoff** — Failed deliveries retry with exponential backoff (1s → 2s → 4s → ... up to a max)
- **HMAC signature** — Each delivery is signed with a per-subscriber secret key so subscribers can verify authenticity
- **Dead-letter queue** — Permanently failed deliveries are moved to a DLQ for inspection and manual replay
- **Management API** — Register endpoints, view delivery history, replay failed events
- **Monitoring dashboard** — Streamlit dashboard showing delivery success rates, failure reasons, and queue depth

---

## Architecture

```
[Event Producer]
      │
      ▼
[POST /events]  ──►  [FastAPI Ingest API]
                             │
                             ▼
                       [Redis Queue]
                             │
                             ▼
                     [Celery Workers]
                    /        |        \
                   ▼         ▼         ▼
            [Subscriber 1] [Sub 2]  [Sub 3]
                             │
                    (on failure)
                             ▼
                    [Dead Letter Queue]
                             │
                             ▼
                    [PostgreSQL - delivery log]
                             │
                             ▼
                    [Streamlit Dashboard]
```

---

## Project Structure

```
payment-webhook-engine/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── routers/
│   │   ├── events.py        # POST /events — ingest payment events
│   │   ├── subscribers.py   # CRUD for webhook subscribers
│   │   └── deliveries.py    # Delivery history + replay endpoints
│   ├── models/
│   │   ├── event.py         # Pydantic v2 schemas — Event, Subscriber
│   │   └── delivery.py      # Delivery log schema
│   ├── db/
│   │   ├── database.py      # SQLAlchemy async engine setup
│   │   └── models.py        # ORM models
│   ├── worker/
│   │   ├── celery_app.py    # Celery configuration
│   │   ├── tasks.py         # deliver_event task with retry logic
│   │   └── dlq.py           # Dead-letter queue handler
│   └── utils/
│       └── signing.py       # HMAC-SHA256 signature generation
├── dashboard/
│   └── app.py               # Streamlit monitoring dashboard
├── tests/
│   ├── test_events.py       # pytest — event ingestion tests
│   ├── test_delivery.py     # pytest — delivery + retry logic tests
│   └── test_signing.py      # pytest — HMAC signature tests
├── docker-compose.yml       # FastAPI + Celery + Redis + PostgreSQL
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## Getting Started

### Prerequisites
- Docker & Docker Compose
- Python 3.11+

### Run with Docker

```bash
git clone https://github.com/YOUR_USERNAME/payment-webhook-engine
cd payment-webhook-engine
cp .env.example .env
docker-compose up --build
```

Services started:
- FastAPI API → `http://localhost:8000`
- Streamlit Dashboard → `http://localhost:8501`
- Redis → `localhost:6379`
- PostgreSQL → `localhost:5432`

### Run Locally (without Docker)

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start Redis (required)
redis-server

# Start Celery worker
celery -A app.worker.celery_app worker --loglevel=info

# Start API
uvicorn app.main:app --reload

# Start dashboard (separate terminal)
streamlit run dashboard/app.py
```

---

## API Reference

### Register a Subscriber
```http
POST /subscribers
Content-Type: application/json

{
  "name": "MerchantA",
  "url": "https://merchant-a.com/webhooks",
  "events": ["payment.success", "payment.failed"],
  "secret": "your-secret-key"
}
```

### Ingest a Payment Event
```http
POST /events
Content-Type: application/json

{
  "event_type": "payment.success",
  "payload": {
    "transaction_id": "txn_001",
    "amount": 5000,
    "currency": "INR",
    "status": "SUCCESS"
  }
}
```

### Replay a Failed Delivery
```http
POST /deliveries/{delivery_id}/replay
```

### View Delivery History
```http
GET /deliveries?subscriber_id=1&status=failed&limit=50
```

---

## Webhook Signature Verification

Every delivery includes an `X-Webhook-Signature` header. Subscribers can verify it:

```python
import hmac, hashlib

def verify_signature(payload: bytes, secret: str, signature: str) -> bool:
    expected = hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

---

## Running Tests

```bash
pytest tests/ -v
```

Test coverage includes:
- Event ingestion validation (valid/invalid payloads)
- Delivery retry logic (mock subscriber endpoints)
- HMAC signature generation and verification
- Dead-letter queue routing on max retry exceeded

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| Celery + Redis for queuing | Decouples ingestion from delivery; Redis acts as both broker and result backend |
| Exponential backoff | Avoids thundering herd on transient subscriber failures |
| HMAC-SHA256 signing | Industry standard (same as Stripe/GitHub webhooks); prevents spoofed deliveries |
| PostgreSQL for delivery log | Durable audit trail; supports replay and analytics queries |
| Dead-letter queue | Prevents silent data loss on permanent failures |

---

## Roadmap
- [ ] Webhook endpoint health checks (auto-disable failing subscribers)
- [ ] Rate limiting per subscriber
- [ ] Event filtering per subscriber (subscribe to specific event types only)
- [ ] Deploy to Railway / Render with live demo
