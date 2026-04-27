import { useState } from 'react'
import { createPayout } from '../api'
import { v4 as uuidv4 } from 'uuid'

export default function PayoutForm({ merchant, bankAccounts, availablePaise, onSuccess }) {
  const [amount, setAmount] = useState('')
  const [bankId, setBankId] = useState(bankAccounts[0]?.id || '')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState(null)

  const fmt = (p) => `₹${(p / 100).toLocaleString('en-IN')}`

  const handleSubmit = async () => {
    const amountPaise = Math.round(parseFloat(amount) * 100)
    if (!amountPaise || amountPaise <= 0) {
      setMessage({ type: 'error', text: 'Enter a valid amount' })
      return
    }
    if (amountPaise > availablePaise) {
      setMessage({ type: 'error', text: `Max available: ${fmt(availablePaise)}` })
      return
    }

    setLoading(true)
    setMessage(null)

    const idempotencyKey = uuidv4()
    const { ok, body } = await createPayout(
      { merchant_id: merchant.id, amount_paise: amountPaise, bank_account_id: bankId },
      idempotencyKey
    )

    setLoading(false)

    if (ok) {
      setMessage({ type: 'success', text: `Payout of ${fmt(amountPaise)} queued` })
      setAmount('')
      onSuccess()
    } else {
      setMessage({ type: 'error', text: body.error || 'Request failed' })
    }
  }

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6">
      <h2 className="text-zinc-400 text-xs uppercase tracking-widest mb-4">Request Payout</h2>

      <div className="space-y-4">
        <div>
          <label className="text-zinc-500 text-xs mb-1 block">Amount (₹)</label>
          <input
            type="number"
            value={amount}
            onChange={e => setAmount(e.target.value)}
            placeholder="0.00"
            className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-zinc-100 font-mono focus:outline-none focus:border-emerald-500"
          />
          <div className="text-zinc-600 text-xs mt-1">Available: {fmt(availablePaise)}</div>
        </div>

        <div>
          <label className="text-zinc-500 text-xs mb-1 block">Bank Account</label>
          <select
            value={bankId}
            onChange={e => setBankId(e.target.value)}
            className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-zinc-100 focus:outline-none focus:border-emerald-500"
          >
            {bankAccounts.map(b => (
              <option key={b.id} value={b.id}>
                {b.account_holder_name} — {b.account_number}
              </option>
            ))}
          </select>
        </div>

        {message && (
          <div className={`text-sm px-3 py-2 rounded ${
            message.type === 'success'
              ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
              : 'bg-red-950 text-red-400 border border-red-800'
          }`}>
            {message.text}
          </div>
        )}

        <button
          onClick={handleSubmit}
          disabled={loading}
          className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-bold py-2 rounded transition-colors"
        >
          {loading ? 'Submitting...' : 'Request Payout'}
        </button>
      </div>
    </div>
  )
}