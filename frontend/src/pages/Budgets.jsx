import { useState, useEffect } from 'react'
import { api, getMonthOptions } from '../api'

export default function Budgets({ month, categories }) {
  const [status, setStatus] = useState(null)
  const [limits, setLimits] = useState({})
  const [loading, setLoading] = useState(true)
  const [copyFrom, setCopyFrom] = useState('')

  useEffect(() => {
    setLoading(true)
    api.getBudgetStatus(month).then(data => {
      setStatus(data)
      const cur = {}; data.rows.forEach(r => cur[r.category_id] = r.limit)
      setLimits(cur)
    }).finally(() => setLoading(false))
  }, [month])

  const budgetable = categories.filter(c => !c.exclude_from_budget)

  const handleSave = async () => {
    const orig = {}; status.rows.forEach(r => orig[r.category_id] = r.limit)
    for (const c of budgetable) {
      const o = orig[c.id] || 0, n = limits[c.id] || 0
      if (n !== o) {
        if (n > 0) await api.setBudget({ category_id: c.id, month, limit: n })
        else await api.deleteBudget(c.id, month)
      }
    }
    const data = await api.getBudgetStatus(month); setStatus(data)
    alert('Saved!')
  }

  const handleCopy = async () => {
    if (!copyFrom) return
    const r = await api.copyBudgets(copyFrom, month)
    alert(`Copied ${r.copied}`)
    const data = await api.getBudgetStatus(month); setStatus(data)
    const cur = {}; data.rows.forEach(r => cur[r.category_id] = r.limit); setLimits(cur)
  }

  if (loading) return <div>Loading...</div>

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Budgets · {month}</h1>
      <div className="bg-white rounded-xl shadow-sm border mb-6">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b"><tr><th className="text-left p-3">Category</th><th className="text-right p-3">Limit</th></tr></thead>
          <tbody>
            {budgetable.map(c => (
              <tr key={c.id} className="border-b"><td className="p-3">{c.emoji} {c.name}</td>
                <td className="p-3 text-right">
                  <input type="number" step="10" min="0" value={limits[c.id] || ''} onChange={e => setLimits({...limits, [c.id]: parseFloat(e.target.value) || 0})}
                    className="w-32 p-2 border rounded-lg text-right" placeholder="$0"/>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex gap-4">
        <button onClick={handleSave} className="px-6 py-2 bg-blue-600 text-white rounded-lg">Save</button>
        <select value={copyFrom} onChange={e => setCopyFrom(e.target.value)} className="p-2 border rounded-lg">
          <option value="">Copy from...</option>
          {getMonthOptions().filter(m => m !== month).map(m => <option key={m} value={m}>{m}</option>)}
        </select>
        <button onClick={handleCopy} disabled={!copyFrom} className="px-4 py-2 bg-gray-100 rounded-lg disabled:opacity-50">Copy</button>
      </div>
    </div>
  )
}
