import { useState, useEffect } from 'react'
import { createPayout } from '../api'
import { v4 as uuidv4 } from 'uuid'

export default function PayoutForm({ merchant, bankAccounts, availablePaise, onSuccess }) {
  const [amount, setAmount] = useState('')
  const [bankId, setBankId] = useState(bankAccounts[0]?.id || '')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState(null)

  useEffect(() => {
    if (bankAccounts.length > 0 && !bankId) {
      setBankId(bankAccounts[0].id)
    }
  }, [bankAccounts])

  const fmt = p => `₹${(p / 100).toLocaleString('en-IN')}`
  const numericAmount = amount ? parseFloat(amount) : 0
  const pct = Number.isFinite(numericAmount) && availablePaise > 0 ? Math.min((numericAmount * 100) / availablePaise * 100, 100) : 0

  const handleSubmit = async () => {
    const amountPaise = Math.round(parseFloat(amount) * 100)
    if (!amountPaise || amountPaise <= 0) {
      setMessage({ type: 'error', text: 'Enter a valid amount' })
      return
    }
    if (amountPaise > availablePaise) {
      setMessage({ type: 'error', text: `Max: ${fmt(availablePaise)}` })
      return
    }
    if (!bankId) {
      setMessage({ type: 'error', text: 'Select a bank account' })
      return
    }

    setLoading(true)
    setMessage(null)
    const { ok, body } = await createPayout(
      { merchant_id: merchant.id, amount_paise: amountPaise, bank_account_id: bankId },
      uuidv4()
    )
    setLoading(false)
    if (ok) {
      setMessage({ type: 'success', text: `Payout of ${fmt(amountPaise)} queued successfully` })
      setAmount('')
      onSuccess()
    } else {
      setMessage({ type: 'error', text: body.error || 'Request failed' })
    }
  }

  return (
    <div
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: '12px',
        padding: '1.5rem'
      }}
    >
      <div style={{ fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.12em', marginBottom: '1.25rem' }}>
        Request payout
      </div>

      <div style={{ marginBottom: '1rem' }}>
        <label style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>Amount (₹)</label>
        <input
          type="number"
          value={amount}
          onChange={e => setAmount(e.target.value)}
          placeholder="0.00"
          style={{
            width: '100%',
            padding: '10px 12px',
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border-bright)',
            borderRadius: '8px',
            color: 'var(--text-primary)',
            fontFamily: "'JetBrains Mono'",
            fontSize: '18px',
            outline: 'none',
            transition: 'border-color 0.15s, box-shadow 0.15s'
          }}
          onFocus={e => {
            e.target.style.borderColor = 'var(--cyan)'
            e.target.style.boxShadow = '0 0 0 3px rgba(42, 170, 195, 0.18)'
          }}
          onBlur={e => {
            e.target.style.borderColor = 'var(--border-bright)'
            e.target.style.boxShadow = 'none'
          }}
        />
        {/* Progress bar showing % of available balance */}
        <div style={{ marginTop: '8px' }}>
          <div style={{ height: '3px', background: 'var(--bg-elevated)', borderRadius: '2px', overflow: 'hidden' }}>
            <div
              style={{
                height: '100%',
                width: `${pct}%`,
                background: pct > 90 ? 'var(--red)' : pct > 60 ? 'var(--amber)' : 'var(--cyan)',
                transition: 'width 0.2s ease, background 0.2s ease',
                borderRadius: '2px'
              }}
            />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{pct.toFixed(1)}% of available</span>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: "'JetBrains Mono'" }}>Max {fmt(availablePaise)}</span>
          </div>
        </div>
      </div>

      <div style={{ marginBottom: '1.25rem' }}>
        <label style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>Bank account</label>
        <select
          value={bankId}
          onChange={e => setBankId(e.target.value)}
          style={{
            width: '100%',
            padding: '10px 12px',
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border-bright)',
            borderRadius: '8px',
            color: 'var(--text-primary)',
            fontFamily: "'Syne', sans-serif",
            fontSize: '13px',
            outline: 'none',
            cursor: 'pointer'
          }}
          onFocus={e => {
            e.target.style.borderColor = 'var(--cyan)'
            e.target.style.boxShadow = '0 0 0 3px rgba(42, 170, 195, 0.18)'
          }}
          onBlur={e => {
            e.target.style.borderColor = 'var(--border-bright)'
            e.target.style.boxShadow = 'none'
          }}
        >
          {bankAccounts.length === 0 && <option>No accounts found</option>}
          {bankAccounts.map(b => (
            <option key={b.id} value={b.id} style={{ background: 'var(--bg-elevated)' }}>
              {b.account_holder_name} · {b.account_number} · {b.ifsc_code}
            </option>
          ))}
        </select>
      </div>

      {message && (
        <div
          style={{
            padding: '10px 12px',
            borderRadius: '8px',
            marginBottom: '1rem',
            fontSize: '12px',
            background: message.type === 'success' ? 'var(--green-dim)' : 'var(--red-dim)',
            border: `1px solid ${message.type === 'success' ? 'var(--green)' : 'var(--red)'}`,
            color: message.type === 'success' ? 'var(--green)' : 'var(--red)',
            fontFamily: "'JetBrains Mono'"
          }}
        >
          {message.type === 'success' ? '✓ ' : '✗ '}
          {message.text}
        </div>
      )}

      <button
        onClick={handleSubmit}
        disabled={loading || !bankId}
        style={{
          width: '100%',
          padding: '12px',
          background: loading ? 'var(--bg-elevated)' : 'var(--cyan-dim)',
          border: `1px solid ${loading ? 'var(--border)' : 'var(--cyan)'}`,
          borderRadius: '8px',
          color: loading ? 'var(--text-muted)' : 'var(--cyan)',
          fontFamily: "'Syne', sans-serif",
          fontWeight: '600',
          fontSize: '13px',
          letterSpacing: '0.06em',
          cursor: loading ? 'not-allowed' : 'pointer',
          transition: 'all 0.15s ease',
          textTransform: 'none'
        }}
      >
        {loading ? 'Processing...' : 'Initiate payout →'}
      </button>
    </div>
  )
}