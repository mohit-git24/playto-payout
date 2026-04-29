import { useState, useEffect } from 'react'
import { getMerchants } from './api'
import Dashboard from './components/Dashboard'

export default function App() {
  const [merchants, setMerchants] = useState([])
  const [selectedId, setSelectedId] = useState(null)

  useEffect(() => {
    getMerchants().then(data => {
      setMerchants(data)
      if (data.length > 0) setSelectedId(data[0].id)
    })
  }, [])

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'var(--bg-base)',
        color: 'var(--text-primary)',
        fontFamily: "'Syne', sans-serif"
      }}
    >
      {/* Top Navigation Bar */}
      <header
        style={{
          borderBottom: '1px solid var(--border)',
          padding: '0 2rem',
          height: '56px',
          display: 'flex',
          alignItems: 'center',
          gap: '1rem',
          background: 'var(--bg-surface)',
          position: 'sticky',
          top: 0,
          zIndex: 100,
          backdropFilter: 'blur(12px)'
        }}
      >
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginRight: '2rem' }}>
          <div
            style={{
              width: '28px',
              height: '28px',
              background: 'linear-gradient(135deg, var(--gold), var(--amber))',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '14px',
              fontWeight: '800'
            }}
          >
            ₹
          </div>
          <span style={{ fontWeight: '800', fontSize: '15px', letterSpacing: '0.05em', color: 'var(--text-primary)' }}>
            PLAYTO
          </span>
          <span style={{ fontWeight: '400', fontSize: '13px', color: 'var(--text-muted)', letterSpacing: '0.1em' }}>
            PAY
          </span>
        </div>

        {/* Live indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginRight: 'auto' }}>
          <div
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              background: 'var(--green)',
              boxShadow: '0 0 8px var(--green)',
              animation: 'pulse 2s infinite'
            }}
          />
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.08em' }}>LIVE</span>
        </div>

        {/* Merchant Tabs */}
        <div style={{ display: 'flex', gap: '4px' }}>
          {merchants.map(m => (
            <button
              key={m.id}
              onClick={() => setSelectedId(m.id)}
              style={{
                padding: '6px 14px',
                borderRadius: '6px',
                border: selectedId === m.id ? '1px solid var(--cyan)' : '1px solid var(--border)',
                background: selectedId === m.id ? 'var(--cyan-dim)' : 'transparent',
                color: selectedId === m.id ? 'var(--cyan)' : 'var(--text-secondary)',
                fontSize: '12px',
                fontFamily: "'Syne', sans-serif",
                fontWeight: selectedId === m.id ? '600' : '400',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                letterSpacing: '0.03em'
              }}
            >
              {m.name}
            </button>
          ))}
        </div>
      </header>

      {selectedId && <Dashboard merchantId={selectedId} />}

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(12px); }
          to { opacity: 1; transform: translateY(0); }
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: var(--bg-base); }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: var(--bg-base); }
        ::-webkit-scrollbar-thumb { background: var(--border-bright); border-radius: 2px; }
      `}</style>
    </div>
  )
}
