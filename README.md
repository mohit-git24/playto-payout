# Playto Payout Engine

Cross-border payout infrastructure for Indian merchants. Handles balance ledger, concurrent payout requests, idempotency, background processing, and retry logic.

**Live:** https://playto-payout-six.vercel.app
**API:** https://playto-payout-q7kd.onrender.com/api/v1

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 4.2 + Django REST Framework |
| Database | PostgreSQL (Supabase) |
| Queue | Celery 5.3 + Redis (Upstash) |
| Frontend | React 18 + Vite |
| Hosting | Render (backend) + Vercel (frontend) |

---

## Local Setup

### Prerequisites
- Python 3.11+
- Node 20+
- PostgreSQL running locally
- Redis running locally

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # edit with your DB credentials
python manage.py migrate
python seed.py
python manage.py runserver
```

### Celery Worker (separate terminal)

```bash
cd backend
source venv/bin/activate
celery -A config worker --beat --loglevel=info
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at http://localhost:5173
Backend runs at http://localhost:8000

---

## Environment Variables

Create `backend/.env`:

```env
DB_NAME=playto_payout
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_HOST=localhost
DB_PORT=5432
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key
DEBUG=True
```

---

## API Reference

### List merchants
```
GET /api/v1/merchants/
```

### Merchant detail + balance + ledger
```
GET /api/v1/merchants/{id}/
```

### Create payout
```
POST /api/v1/payouts/
Headers:
  Idempotency-Key: <uuid-v4>
  Content-Type: application/json

Body:
{
  "merchant_id": "uuid",
  "amount_paise": 50000,
  "bank_account_id": "uuid"
}
```

### Get payout status
```
GET /api/v1/payouts/{id}/
```

---

## Seed Data

```bash
python seed.py
```

Creates 3 merchants with credit history:
- Aryan Design Studio — ₹5,25,000
- Priya Freelance Dev — ₹4,70,000
- Nexus Marketing Agency — ₹7,75,000

---

## Run Tests

```bash
cd backend
python manage.py test payouts --verbosity=2
```

---

## Docker

```bash
docker-compose up --build
docker-compose exec backend python manage.py migrate
docker-compose exec backend python seed.py
```

---

## Architecture

```
Frontend (React)
     │
     ▼
Django REST API
     │
     ├── PostgreSQL (ledger, payouts, merchants)
     │
     └── Celery Worker ──► Redis (task queue)
              │
              ▼
        Bank Simulation
        (70% success, 20% fail, 10% hang)
```

## Key Design Decisions

**Money as integers:** All amounts in paise (`BigIntegerField`). No floats, no decimals. ₹10 = `1000`.

**Ledger model:** Balance derived from `SUM(credits) - SUM(debits)` via DB aggregation. Never stored as mutable field.

**Concurrency:** `SELECT FOR UPDATE` on merchant row inside `transaction.atomic()`. Second concurrent request blocks at DB level until first commits.

**Idempotency:** Three layers — fast path query, re-check inside lock, database unique constraint as final safety net.

**State machine:** `pending → processing → completed/failed`. Terminal states have no exits. Enforced at model level via `transition_to()`.

**Fund return:** Failed payouts write no debit entry. Funds become available automatically since `available = credits - debits - held`.