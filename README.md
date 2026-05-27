# Payment Webhook Delivery Engine

A production-style webhook delivery system built with Python — accepts payment events, queues them reliably, and delivers to subscriber endpoints with retry logic, HMAC signature verification, and a live monitoring dashboard.

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

## What This Project Is

When you pay via Razorpay or Stripe, the payment provider doesn't just process the transaction and stop there. It also needs to tell *your* server that it happened — so you can update order status, trigger a dispatch, send a receipt, whatever. That notification mechanism is a **webhook**.

The catch is: a webhook is just an HTTP POST from their system to yours, and your server could be down, slow, or returning errors at exactly the wrong moment. So any serious payment platform needs to:

- queue the event so it isn't lost if delivery fails
- retry on failure with a backoff strategy that doesn't hammer the endpoint
- sign each delivery so the receiver can verify it actually came from you
- track what got delivered, what failed, and why — with the ability to replay

This project builds exactly that infrastructure. It's the kind of system that lives inside Razorpay, Stripe, or any payments platform that needs to push events reliably to third-party merchant endpoints.

**What it does:**

- **Event ingestion** — Payment events (`payment.success`, `payment.failed`, `payment.refunded`) are submitted via REST API
- **Reliable queuing** — Events are handed off to Celery + Redis immediately, so the API response is fast and delivery happens asynchronously
- **Subscriber delivery** — Events are fanned out to all registered HTTP endpoints that subscribe to that event type
- **Retry with backoff** — Failed deliveries retry with exponential backoff (1s → 2s → 4s → up to 5 attempts total)
- **HMAC signature** — Each delivery is signed with a per-subscriber secret so recipients can verify authenticity
- **Dead-letter queue** — Events that exhaust all retries are moved to a DLQ for inspection and manual replay
- **Management API** — Register endpoints, view delivery history, replay failed events
- **Web UI** — A clean browser-based dashboard for managing everything without touching Swagger

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
│   ├── main.py              # FastAPI app entry point (with CORS middleware)
│   ├── routers/
│   │   ├── events.py        # POST /events — ingest payment events
│   │   ├── subscribers.py   # CRUD for webhook subscribers (incl. PATCH update)
│   │   └── deliveries.py    # Delivery history + replay endpoints
│   ├── models/
│   │   ├── event.py         # Pydantic v2 schemas — Event, Subscriber, SubscriberUpdate
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
├── ui.html                  # Standalone web UI (open directly in browser)
├── docker-compose.yml       # FastAPI + Celery + Redis + PostgreSQL + Streamlit
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## What's New

### Web UI (`ui.html`)

The project now ships with a standalone HTML dashboard that you open directly in a browser — no build step, no npm, no local server. It talks to the API at `http://localhost:8000`.

**Four tabs:**

- **Send Event** — pick an event type, fill in transaction details, click send. Shows the returned event ID and timestamp on success.
- **Subscribers** — register new webhook endpoints, edit existing ones (name, URL, secret, subscribed events), deactivate, or delete. Each card shows live status and subscribed event types.
- **Delivery History** — filterable table of all delivery attempts with color-coded status badges (green for success, red for failed, orange for dead letter). Every row has a Replay button.
- **Dead Letter Queue** — events that exhausted all 5 retry attempts, with the exact error message from the last attempt and one-click replay.

To open it, with the Docker stack running:

```bash
open ui.html          # macOS
xdg-open ui.html      # Linux
start ui.html         # Windows
```

### CORS Support

`main.py` now includes CORS middleware (`allow_origins=["*"]`). This is what lets `ui.html` — opened as a local `file://` URL — make API calls to the backend without being blocked by the browser's same-origin policy.

### Edit Subscriber (`PATCH /subscribers/{id}`)

The original API only supported create, deactivate, and delete for subscribers. There's now a proper partial-update endpoint that accepts any combination of `name`, `url`, `events`, and `secret` as optional fields. Useful for fixing a misconfigured URL, swapping a compromised secret, or changing which event types an endpoint listens to — without deleting and recreating the subscriber.

---

## Getting Started

### Prerequisites

- Docker Desktop installed and running
- Git

No local Python installation is needed to run the project — everything runs in containers.

### Run with Docker

```bash
git clone https://github.com/YOUR_USERNAME/payment-webhook-engine
cd payment-webhook-engine
docker compose up --build
```

This starts 5 services:

| Service | What it does | Available at |
|---|---|---|
| `api` | FastAPI REST API | http://localhost:8000 |
| `worker` | Celery delivery worker | — (background process) |
| `dashboard` | Streamlit monitoring dashboard | http://localhost:8501 |
| `db` | PostgreSQL — delivery logs & subscribers | localhost:5432 |
| `redis` | Redis — task broker & dead-letter queue | localhost:6379 |

### Open the Web UI

With Docker running, open `ui.html` from the project root:

```bash
open ui.html    # macOS
```

The UI will load in your browser and connect to the API at `http://localhost:8000`.

### Open the Swagger Docs

Interactive API docs are at: **http://localhost:8000/docs**

The Streamlit dashboard is at: **http://localhost:8501**

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

## How to Test

Here's a full end-to-end walkthrough that exercises every part of the system.

**Step 1 — Get a live test endpoint**

Go to [https://webhook.site](https://webhook.site) and copy your unique URL (looks like `https://webhook.site/xxxxxxxx-xxxx-...`). This gives you a real HTTP endpoint you can inspect in real time — you'll see every request that hits it.

**Step 2 — Register a subscriber**

Open `ui.html` → go to the **Subscribers** tab → fill in the Add Subscriber form:
- Name: `Test Merchant`
- URL: your webhook.site URL
- Secret: `mysecret`
- Events: check `payment.success`

Click **Add Subscriber**. The card should appear below.

Or via curl if you prefer:
```bash
curl -X POST http://localhost:8000/subscribers/ \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Merchant","url":"YOUR_WEBHOOKSITE_URL","events":["payment.success"],"secret":"mysecret"}'
```

**Step 3 — Send a payment event**

Switch to the **Send Event** tab → select `payment.success`, enter a transaction ID like `TXN001` and an amount → click **Send Event**. The returned event ID confirms it was queued.

Or via curl:
```bash
curl -X POST http://localhost:8000/events/ \
  -H "Content-Type: application/json" \
  -d '{"event_type":"payment.success","payload":{"transaction_id":"TXN001","amount":1500,"currency":"INR"}}'
```

**Step 4 — Verify on webhook.site**

Switch back to webhook.site — the delivery should arrive within a second or two. Check the request headers: you'll see `X-Webhook-Signature`, `X-Webhook-Event`, and `X-Webhook-Delivery-ID`. The body is the payload you sent.

**Step 5 — View delivery history**

Open the **Delivery History** tab → click Refresh. The delivery shows up with a green `Success` badge.

**Step 6 — Test retry behavior**

Register a second subscriber with a URL that'll definitely fail — `http://localhost:9999` works fine. Send another event. The worker will attempt delivery, get a connection error, and retry with exponential backoff. After 5 attempts it gives up and moves the event to the dead letter queue. You can watch the status change in Delivery History (hit Refresh a few times).

**Step 7 — Check the Dead Letter Queue**

Go to the **Dead Letter Queue** tab. The failed event is there with its error message. Once you've fixed the subscriber's endpoint, hit **Replay** — the system re-queues the delivery immediately.

---

## API Reference

### Register a Subscriber
```http
POST /subscribers/
Content-Type: application/json

{
  "name": "MerchantA",
  "url": "https://merchant-a.com/webhooks",
  "events": ["payment.success", "payment.failed"],
  "secret": "your-secret-key"
}
```

### Update a Subscriber
```http
PATCH /subscribers/{subscriber_id}
Content-Type: application/json

{
  "name": "Updated Name",
  "url": "https://new-endpoint.com/webhooks",
  "events": ["payment.success", "payment.refunded"],
  "secret": "rotated-secret"
}
```

All fields are optional — only the ones present in the request body are updated.

### Ingest a Payment Event
```http
POST /events/
Content-Type: application/json

{
  "event_type": "payment.success",
  "payload": {
    "transaction_id": "txn_001",
    "amount": 5000,
    "currency": "INR",
    "status": "completed"
  }
}
```

### Replay a Failed Delivery
```http
POST /deliveries/{delivery_id}/replay
```

### View Delivery History
```http
GET /deliveries/?subscriber_id=1&status=failed&limit=50
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
| Single-file UI | No build toolchain required; works opened directly as a local file |
| CORS on `*` | Lets the local `ui.html` file call the API without proxy or server setup |

---

## Roadmap
- [ ] Webhook endpoint health checks (auto-disable failing subscribers)
- [ ] Rate limiting per subscriber
- [ ] Event filtering per subscriber (subscribe to specific event types only)
- [ ] Deploy to Railway / Render with live demo
