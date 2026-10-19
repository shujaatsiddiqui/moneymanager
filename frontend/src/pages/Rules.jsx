import { useState, useEffect } from 'react'
import { api } from '../api'

export default function Rules({ categories }) {
  const [rules, setRules] = useState([])
  const [loading, setLoading] = useState(true)
  const [pattern, setPattern] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [priority, setPriority] = useState(100)
  const [minAmount, setMinAmount] = useState('')
  const [maxAmount, setMaxAmount] = useState('')

  const load = () => { setLoading(true); api.getRules().then(setRules).finally(() => setLoading(false)) }
  useEffect(load, [])

  const flatCats = []
  categories.forEach(c => { flatCats.push({ id: c.id, name: `${c.emoji} ${c.name}` }); c.children?.forEach(s => flatCats.push({ id: s.id, name: `  └ ${s.name}` })) })

  const handleAdd = async e => {
    e.preventDefault()
    if (!pattern || !categoryId) return
    const rule = {
      pattern,
      category_id: parseInt(categoryId),
      priority: parseInt(priority),
    }
    if (minAmount) rule.min_amount = parseFloat(minAmount)
    if (maxAmount) rule.max_amount = parseFloat(maxAmount)
    await api.createRule(rule)
    setPattern(''); setCategoryId(''); setPriority(100); setMinAmount(''); setMaxAmount('')
    load()
  }

  const handleDel = async id => { if (!confirm('Delete?')) return; await api.deleteRule(id); load() }
  const handleApply = async () => { const r = await api.applyRules(); alert(`Categorized ${r.categorized}`) }

  const formatAmount = (min, max) => {
    if (min && max && min === max) return `$${min}`
    if (min && max) return `$${min} - $${max}`
    if (min) return `>= $${min}`
    if (max) return `<= $${max}`
    return ''
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Category Rules</h1>
      <p className="text-gray-500 mb-6">Pattern matching for auto-categorization. Use <code className="bg-gray-100 px-1 rounded">re:</code> for regex.</p>
      {loading ? <div>Loading...</div> : <>
        {rules.length > 0 && <div className="bg-white rounded-xl shadow-sm border mb-6">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left p-3">Pattern</th>
                <th className="text-left p-3">Amount</th>
                <th className="text-left p-3">Category</th>
                <th className="text-right p-3">Priority</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rules.map(r => (
                <tr key={r.id} className="border-b">
                  <td className="p-3 font-mono">{r.pattern}</td>
                  <td className="p-3 text-gray-600">{formatAmount(r.min_amount, r.max_amount) || '—'}</td>
                  <td className="p-3">{r.category}</td>
                  <td className="p-3 text-right">{r.priority}</td>
                  <td className="p-3 text-right"><button onClick={() => handleDel(r.id)} className="text-red-600">Delete</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>}

        <form onSubmit={handleAdd} className="bg-white p-6 rounded-xl shadow-sm border max-w-xl mb-6">
          <h3 className="font-medium mb-4">Add Rule</h3>
          <div className="mb-4">
            <label className="block text-sm mb-1">Pattern</label>
            <input type="text" value={pattern} onChange={e => setPattern(e.target.value)} className="w-full p-2 border rounded-lg" placeholder="STARBUCKS"/>
          </div>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm mb-1">Min Amount</label>
              <input type="number" step="0.01" value={minAmount} onChange={e => setMinAmount(e.target.value)} className="w-full p-2 border rounded-lg" placeholder="Optional"/>
            </div>
            <div>
              <label className="block text-sm mb-1">Max Amount</label>
              <input type="number" step="0.01" value={maxAmount} onChange={e => setMaxAmount(e.target.value)} className="w-full p-2 border rounded-lg" placeholder="Optional"/>
            </div>
          </div>
          <p className="text-xs text-gray-500 mb-4">For exact amount, set both min and max to the same value.</p>
          <div className="mb-4">
            <label className="block text-sm mb-1">Category</label>
            <select value={categoryId} onChange={e => setCategoryId(e.target.value)} className="w-full p-2 border rounded-lg">
              <option value="">Select</option>
              {flatCats.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div className="mb-4">
            <label className="block text-sm mb-1">Priority (lower runs first)</label>
            <input type="number" value={priority} onChange={e => setPriority(e.target.value)} className="w-full p-2 border rounded-lg"/>
          </div>
          <button type="submit" disabled={!pattern || !categoryId} className="w-full py-2 bg-blue-600 text-white rounded-lg disabled:opacity-50">Add Rule</button>
        </form>

        <button onClick={handleApply} className="px-6 py-2 bg-gray-100 rounded-lg hover:bg-gray-200">Apply Rules to Uncategorized</button>
      </>}
    </div>
  )
}
