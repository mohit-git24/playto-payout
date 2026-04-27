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
    <div className="min-h-screen bg-zinc-950 text-zinc-100 font-mono">
      <header className="border-b border-zinc-800 px-8 py-4 flex items-center gap-6">
        <span className="text-emerald-400 font-bold text-xl tracking-tight">PLAYTO PAY</span>
        <span className="text-zinc-500 text-sm">Payout Engine</span>
        <div className="ml-auto flex gap-2">
          {merchants.map(m => (
            <button
              key={m.id}
              onClick={() => setSelectedId(m.id)}
              className={`px-3 py-1 rounded text-xs border transition-all ${
                selectedId === m.id
                  ? 'border-emerald-500 text-emerald-400 bg-emerald-950'
                  : 'border-zinc-700 text-zinc-400 hover:border-zinc-500'
              }`}
            >
              {m.name}
            </button>
          ))}
        </div>
      </header>
      {selectedId && <Dashboard merchantId={selectedId} />}
    </div>
  )
}
