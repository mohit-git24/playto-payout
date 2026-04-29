export default function PayoutTable({ payouts }) {
  const fmt = p => `₹${(p / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`

  const STATUS_CONFIG = {
    pending: { color: 'var(--text-secondary)', bg: 'var(--bg-elevated)', border: 'var(--border)', dot: '#7a8fa8' },
    processing: { color: 'var(--amber)', bg: 'var(--amber-dim)', border: 'var(--amber)', dot: '#ffab00' },
    completed: { color: 'var(--green)', bg: 'var(--green-dim)', border: 'var(--green)', dot: '#00e676' },
    failed: { color: 'var(--red)', bg: 'var(--red-dim)', border: 'var(--red)', dot: '#ff3d57' }
  }

  return (
    <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: '12px', overflow: 'hidden' }}>
      <div
        style={{
          padding: '1.25rem 1.5rem',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}
      >
        <span style={{ fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.15em' }}>PAYOUT HISTORY</span>
        <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: "'JetBrains Mono'" }}>{payouts.length} RECORDS</span>
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid var(--border)' }}>
            {['TX ID', 'AMOUNT', 'STATUS', 'ATTEMPTS', 'CREATED', 'NOTE'].map(h => (
              <th
                key={h}
                style={{
                  padding: '10px 16px',
                  textAlign: 'left',
                  fontSize: '9px',
                  color: 'var(--text-muted)',
                  letterSpacing: '0.15em',
                  fontFamily: "'Syne'",
                  fontWeight: '600'
                }}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {payouts.length === 0 && (
            <tr>
              <td colSpan={6} style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                No payouts yet
              </td>
            </tr>
          )}
          {payouts.map(p => {
            const cfg = STATUS_CONFIG[p.status] || STATUS_CONFIG.pending
            return (
              <tr
                key={p.id}
                style={{ borderBottom: '1px solid var(--border)', transition: 'background 0.1s' }}
                onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                <td style={{ padding: '12px 16px', fontFamily: "'JetBrains Mono'", fontSize: '11px', color: 'var(--text-muted)' }}>
                  {p.id.slice(0, 8).toUpperCase()}
                </td>
                <td style={{ padding: '12px 16px', fontFamily: "'JetBrains Mono'", fontSize: '14px', fontWeight: '600', color: 'var(--text-primary)' }}>
                  {fmt(p.amount_paise)}
                </td>
                <td style={{ padding: '12px 16px' }}>
                  <span
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '3px 10px',
                      borderRadius: '20px',
                      background: cfg.bg,
                      border: `1px solid ${cfg.border}`,
                      color: cfg.color,
                      fontSize: '10px',
                      fontFamily: "'JetBrains Mono'",
                      letterSpacing: '0.08em'
                    }}
                  >
                    <span
                      style={{
                        width: '5px',
                        height: '5px',
                        borderRadius: '50%',
                        background: cfg.dot,
                        boxShadow: p.status === 'processing' ? `0 0 6px ${cfg.dot}` : 'none'
                      }}
                    />
                    {p.status.toUpperCase()}
                  </span>
                </td>
                <td style={{ padding: '12px 16px', fontFamily: "'JetBrains Mono'", fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center' }}>
                  {p.attempt_count}
                </td>
                <td style={{ padding: '12px 16px', fontSize: '11px', color: 'var(--text-muted)', fontFamily: "'JetBrains Mono'" }}>
                  {new Date(p.created_at).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'short' })}
                </td>
                <td style={{ padding: '12px 16px', fontSize: '11px', color: 'var(--red)', fontFamily: "'JetBrains Mono'" }}>
                  {p.failure_reason || '—'}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}