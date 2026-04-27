const STATUS_STYLES = {
  pending:    'bg-zinc-800 text-zinc-400',
  processing: 'bg-amber-950 text-amber-400',
  completed:  'bg-emerald-950 text-emerald-400',
  failed:     'bg-red-950 text-red-400',
}

export default function PayoutTable({ payouts }) {
  const fmt = (p) => `₹${(p / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`

  return (
    <div>
      <h2 className="text-zinc-400 text-xs uppercase tracking-widest mb-3">Payout History</h2>
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800">
              <th className="text-left px-4 py-3 text-zinc-500 font-normal">ID</th>
              <th className="text-left px-4 py-3 text-zinc-500 font-normal">Amount</th>
              <th className="text-left px-4 py-3 text-zinc-500 font-normal">Status</th>
              <th className="text-left px-4 py-3 text-zinc-500 font-normal">Created</th>
              <th className="text-left px-4 py-3 text-zinc-500 font-normal">Note</th>
            </tr>
          </thead>
          <tbody>
            {payouts.length === 0 && (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-zinc-600">No payouts yet</td></tr>
            )}
            {payouts.map(p => (
              <tr key={p.id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30 transition-colors">
                <td className="px-4 py-3 text-zinc-500 font-mono text-xs">{p.id.slice(0, 8)}…</td>
                <td className="px-4 py-3 font-mono text-zinc-200">{fmt(p.amount_paise)}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded text-xs font-mono ${STATUS_STYLES[p.status]}`}>
                    {p.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-zinc-500 text-xs">
                  {new Date(p.created_at).toLocaleString('en-IN')}
                </td>
                <td className="px-4 py-3 text-zinc-600 text-xs">{p.failure_reason || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}