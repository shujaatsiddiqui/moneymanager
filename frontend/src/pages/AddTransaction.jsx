import { useState } from 'react'
import { api, formatMoney } from '../api'

export default function AddTransaction({ categories, accounts }) {
  const [kind, setKind] = useState('expense')
  const [date, setDate] = useState(new Date().toISOString().split('T')[0])
  const [amount, setAmount] = useState('')
  const [accountId, setAccountId] = useState(accounts[0]?.id || '')
  const [toAccountId, setToAccountId] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [description, setDescription] = useState('')
  const [note, setNote] = useState('')
  const [isBiz, setIsBiz] = useState(false)
  const [msg, setMsg] = useState(null)

  const flatCats = []
  categories.forEach(c => {
    flatCats.push({ id: c.id, name: `${c.emoji} ${c.name}` })
    c.children?.forEach(s => flatCats.push({ id: s.id, name: `  └ ${s.name}` }))
  })

  const handleSubmit = async e => {
    e.preventDefault()
    if (!amount || parseFloat(amount) <= 0) return
    try {
      const r = await api.createTransaction({
        date, kind, amount: parseFloat(amount), account_id: parseInt(accountId),
        to_account_id: kind === 'transfer' ? parseInt(toAccountId) : null,
        category_id: kind !== 'transfer' && categoryId ? parseInt(categoryId) : null,
        description, note, is_business: isBiz
      })
      let m = `Saved ${formatMoney(r.amount)}`
      if (r.category) m += ` → ${r.category}${r.auto_categorized ? ' (auto)' : ''}`
      setMsg({ type: 'success', text: m })
      setAmount(''); setDescription(''); setNote('')
    } catch (err) { setMsg({ type: 'error', text: err.message }) }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Add Transaction</h1>
      {msg && <div className={`p-4 rounded-lg mb-6 ${msg.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>{msg.text}</div>}
      <form onSubmit={handleSubmit} className="bg-white p-6 rounded-xl shadow-sm border max-w-xl">
        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">Type</label>
          <div className="flex gap-2">
            {['expense','income','transfer'].map(t => (
              <button key={t} type="button" onClick={() => setKind(t)}
                className={`px-4 py-2 rounded-lg capitalize ${kind === t ? 'bg-blue-600 text-white' : 'bg-gray-100'}`}>{t}</button>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div><label className="block text-sm mb-1">Date</label><input type="date" value={date} onChange={e => setDate(e.target.value)} className="w-full p-2 border rounded-lg"/></div>
          <div><label className="block text-sm mb-1">Amount</label><input type="number" step="0.01" value={amount} onChange={e => setAmount(e.target.value)} className="w-full p-2 border rounded-lg" placeholder="0.00"/></div>
        </div>
        <div className="mb-4"><label className="block text-sm mb-1">{kind === 'transfer' ? 'From Account' : 'Account'}</label>
          <select value={accountId} onChange={e => setAccountId(e.target.value)} className="w-full p-2 border rounded-lg">
            {accounts.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
          </select>
        </div>
        {kind === 'transfer' && <div className="mb-4"><label className="block text-sm mb-1">To Account</label>
          <select value={toAccountId} onChange={e => setToAccountId(e.target.value)} className="w-full p-2 border rounded-lg">
            <option value="">Select</option>
            {accounts.filter(a => a.id !== parseInt(accountId)).map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
          </select>
        </div>}
        {kind !== 'transfer' && <div className="mb-4"><label className="block text-sm mb-1">Category</label>
          <select value={categoryId} onChange={e => setCategoryId(e.target.value)} className="w-full p-2 border rounded-lg">
            <option value="">Auto-detect</option>
            {flatCats.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>}
        <div className="mb-4"><label className="block text-sm mb-1">Description</label><input type="text" value={description} onChange={e => setDescription(e.target.value)} className="w-full p-2 border rounded-lg"/></div>
        <div className="mb-4"><label className="block text-sm mb-1">Note</label><input type="text" value={note} onChange={e => setNote(e.target.value)} className="w-full p-2 border rounded-lg"/></div>
        <label className="flex items-center gap-2 mb-6"><input type="checkbox" checked={isBiz} onChange={e => setIsBiz(e.target.checked)} className="rounded"/><span className="text-sm">Business</span></label>
        <button type="submit" disabled={!amount || parseFloat(amount) <= 0} className="w-full py-2 bg-blue-600 text-white rounded-lg disabled:opacity-50">Save</button>
      </form>
    </div>
  )
}
