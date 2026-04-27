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
    refresh()
    const interval = setInterval(refresh, 3000) // poll every 3s for live updates
    return () => clearInterval(interval)
  }, [refresh])

  if (loading) return <div className="p-8 text-zinc-500">Loading...</div>

  const { merchant, balance, ledger_entries, payouts } = data
  const fmt = (paise) => `₹${(paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      {/* Balance Cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6">
          <div className="text-zinc-500 text-xs uppercase tracking-widest mb-2">Total Balance</div>
          <div className="text-2xl font-bold text-zinc-100">{fmt(balance.balance_paise)}</div>
        </div>
        <div className="bg-zinc-900 border border-amber-900/40 rounded-lg p-6">
          <div className="text-amber-500 text-xs uppercase tracking-widest mb-2">Held (In Flight)</div>
          <div className="text-2xl font-bold text-amber-400">{fmt(balance.held_paise)}</div>
        </div>
        <div className="bg-zinc-900 border border-emerald-900/40 rounded-lg p-6">
          <div className="text-emerald-500 text-xs uppercase tracking-widest mb-2">Available</div>
          <div className="text-2xl font-bold text-emerald-400">{fmt(balance.available_paise)}</div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-8">
        <PayoutForm
          merchant={merchant}
          bankAccounts={merchant.bank_accounts || []}
          availablePaise={balance.available_paise}
          onSuccess={refresh}
        />
        <div>
          <h2 className="text-zinc-400 text-xs uppercase tracking-widest mb-3">Recent Credits</h2>
          <div className="space-y-2">
            {ledger_entries.filter(e => e.entry_type === 'credit').slice(0, 5).map(e => (
              <div key={e.id} className="bg-zinc-900 border border-zinc-800 rounded p-3 flex justify-between">
                <span className="text-zinc-400 text-sm truncate">{e.description}</span>
                <span className="text-emerald-400 text-sm font-mono ml-4">+{fmt(e.amount)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <PayoutTable payouts={payouts} />
    </div>
  )
}