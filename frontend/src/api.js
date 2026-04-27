const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const getMerchants = () =>
  fetch(`${BASE}/merchants/`).then(r => r.json());

export const getMerchant = (id) =>
  fetch(`${BASE}/merchants/${id}/`).then(r => r.json());

export const createPayout = (data, idempotencyKey) =>
  fetch(`${BASE}/payouts/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': idempotencyKey,
    },
    body: JSON.stringify(data),
  }).then(r => r.json().then(body => ({ ok: r.ok, status: r.status, body })));

export const getPayout = (id) =>
  fetch(`${BASE}/payouts/${id}/`).then(r => r.json());