import { useState, useEffect, useCallback } from 'react'
import { getMerchant } from '../api'
import PayoutForm from './PayoutForm'
import PayoutTable from './PayoutTable'

export default function Dashboard({ merchantId }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(() => {
    getMerchant(merchantId).then(d => {
      setData(d)
      setLoading(false)
    })
  }, [merchantId])

  useEffect(() => {
    setLoading(true)
    refresh()
    const interval = setInterval(refresh, 3000)
    return () => clearInterval(interval)
  }, [refresh])

  if (loading)
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.15em' }}>LOADING LEDGER...</div>
        </div>
      </div>
    )

  const { merchant, balance, ledger_entries, payouts } = data
  const fmt = p => `₹${(p / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`

  return (
    <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto', animation: 'fadeInUp 0.3s ease' }}>
      {/* Merchant name */}
      <div style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'baseline', gap: '1rem' }}>
        <h1 style={{ fontSize: '22px', fontWeight: '800', color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
          {merchant.name}
        </h1>
        <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontFamily: "'JetBrains Mono'", letterSpacing: '0.05em' }}>
          {merchant.email}
        </span>
      </div>

      {/* Balance Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
        {/* Total Balance */}
        <div
          style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: '12px',
            padding: '1.5rem',
            position: 'relative',
            overflow: 'hidden'
          }}
        >
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              height: '2px',
              background: 'linear-gradient(90deg, var(--gold), transparent)'
            }}
          />
          <div style={{ fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.15em', marginBottom: '0.75rem' }}>
            TOTAL BALANCE
          </div>
          <div style={{ fontSize: '28px', fontWeight: '700', fontFamily: "'JetBrains Mono'", color: 'var(--gold)' }}>
            {fmt(balance.balance_paise)}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '0.5rem' }}>Gross credited funds</div>
        </div>

        {/* Held */}
        <div
          style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: '12px',
            padding: '1.5rem',
            position: 'relative',
            overflow: 'hidden'
          }}
        >
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              height: '2px',
              background:
                balance.held_paise > 0
                  ? 'linear-gradient(90deg, var(--amber), transparent)'
                  : 'linear-gradient(90deg, var(--border), transparent)'
            }}
          />
          <div style={{ fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.15em', marginBottom: '0.75rem' }}>
            HELD · IN FLIGHT
          </div>
          <div
            style={{
              fontSize: '28px',
              fontWeight: '700',
              fontFamily: "'JetBrains Mono'",
              color: balance.held_paise > 0 ? 'var(--amber)' : 'var(--text-muted)'
            }}
          >
            {fmt(balance.held_paise)}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '0.5rem' }}>Pending + processing</div>
        </div>

        {/* Available */}
        <div
          style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: '12px',
            padding: '1.5rem',
            position: 'relative',
            overflow: 'hidden'
          }}
        >
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              height: '2px',
              background: 'linear-gradient(90deg, var(--green), transparent)'
            }}
          />
          <div style={{ fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.15em', marginBottom: '0.75rem' }}>
            AVAILABLE TO WITHDRAW
          </div>
          <div style={{ fontSize: '28px', fontWeight: '700', fontFamily: "'JetBrains Mono'", color: 'var(--green)' }}>
            {fmt(balance.available_paise)}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '0.5rem' }}>Ready for payout</div>
        </div>
      </div>

      {/* Two column layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '2rem' }}>
        <PayoutForm
          merchant={merchant}
          bankAccounts={merchant.bank_accounts || []}
          availablePaise={balance.available_paise}
          onSuccess={refresh}
        />

        {/* Recent Credits */}
        <div
          style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: '12px',
            padding: '1.5rem'
          }}
        >
          <div style={{ fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.15em', marginBottom: '1rem' }}>
            RECENT CREDITS
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {ledger_entries
              .filter(e => e.entry_type === 'credit')
              .slice(0, 5)
              .map(e => (
                <div
                  key={e.id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '10px 12px',
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                    transition: 'border-color 0.15s'
                  }}
                >
                  <span style={{ fontSize: '12px', color: 'var(--text-secondary)', flex: 1, marginRight: '1rem' }}>
                    {e.description}
                  </span>
                  <span style={{ fontSize: '13px', fontFamily: "'JetBrains Mono'", color: 'var(--green)', whiteSpace: 'nowrap' }}>
                    +{fmt(e.amount)}
                  </span>
                </div>
              ))}
          </div>
        </div>
      </div>

      <PayoutTable payouts={payouts} />
    </div>
  )
}