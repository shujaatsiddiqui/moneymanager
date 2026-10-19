import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, formatMoney, getMonthOptions } from '../api'

export default function Transactions({ month, categories }) {
  const [searchParams, setSearchParams] = useSearchParams()
  const [transactions, setTransactions] = useState([])
  const [loading, setLoading] = useState(true)
  const [onlyUncat, setOnlyUncat] = useState(false)
  const [selectedTx, setSelectedTx] = useState(null)
  const [selectedCat, setSelectedCat] = useState('')

  const categoryId = searchParams.get('category')
  const categoryName = searchParams.get('category_name')

  const loadTransactions = async () => {
    setLoading(true)
    const params = { month, uncategorized: onlyUncat }
    if (categoryId) params.category_id = categoryId
    try {
      setTransactions(await api.getTransactions(params))
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadTransactions() }, [month, categoryId, onlyUncat])

  const clearFilter = () => {
    const params = new URLSearchParams(searchParams)
    params.delete('category')
    params.delete('category_name')
    setSearchParams(params)
  }

  const changeMonth = (direction) => {
    const [year, mon] = month.split('-').map(Number)
    let newYear = year, newMonth = mon + direction
    if (newMonth > 12) { newYear++; newMonth = 1 }
    if (newMonth < 1) { newYear--; newMonth = 12 }
    const newMonthStr = `${newYear}-${String(newMonth).padStart(2, '0')}`
    const params = new URLSearchParams(searchParams)
    params.set('month', newMonthStr)
    setSearchParams(params)
  }

  const handleSetCat = async () => {
    if (!selectedTx || !selectedCat) return
    await api.updateTransaction(selectedTx, { category_id: parseInt(selectedCat) })
    await loadTransactions()
    setSelectedTx(null)
    setSelectedCat('')
  }

  const handleDelete = async () => {
    if (!selectedTx || !confirm('Delete?')) return
    await api.deleteTransaction(selectedTx)
    setTransactions(transactions.filter(t => t.id !== selectedTx))
    setSelectedTx(null)
  }

  const selectedTransaction = transactions.find(t => t.id === selectedTx)

  const flatCats = []
  categories.forEach(c => {
    flatCats.push({ id: c.id, name: `${c.emoji} ${c.name}` })
    c.children?.forEach(s => flatCats.push({ id: s.id, name: `  └ ${s.name}` }))
  })

  const monthOptions = getMonthOptions(24)

  // Calculate totals
  const totalExpense = transactions.filter(t => t.kind === 'expense').reduce((a, t) => a + t.amount, 0)
  const totalIncome = transactions.filter(t => t.kind === 'income').reduce((a, t) => a + t.amount, 0)

  return (
    <div>
      {/* Month Navigation */}
      <div className="flex items-center justify-between mb-6">
        <button onClick={() => changeMonth(-1)} className="px-3 py-2 bg-gray-100 rounded-lg hover:bg-gray-200">
          ← Prev
        </button>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-gray-800">Transactions</h1>
          <select
            value={month}
            onChange={(e) => {
              const params = new URLSearchParams(searchParams)
              params.set('month', e.target.value)
              setSearchParams(params)
            }}
            className="text-2xl font-bold text-blue-600 bg-transparent border-none cursor-pointer"
          >
            {monthOptions.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
          {categoryName && <span className="text-xl text-gray-500">· {categoryName}</span>}
        </div>
        <button onClick={() => changeMonth(1)} className="px-3 py-2 bg-gray-100 rounded-lg hover:bg-gray-200">
          Next →
        </button>
      </div>

      {/* Filters & Summary */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={onlyUncat} onChange={e => setOnlyUncat(e.target.checked)} className="rounded"/>
            Only uncategorized
          </label>
          {categoryName && (
            <button onClick={clearFilter} className="px-3 py-1 text-sm bg-gray-100 rounded-lg hover:bg-gray-200">
              ✕ Clear filter
            </button>
          )}
        </div>
        <div className="flex gap-4 text-sm">
          <span>Expenses: <strong className="text-red-600">{formatMoney(totalExpense)}</strong></span>
          <span>Income: <strong className="text-green-600">{formatMoney(totalIncome)}</strong></span>
          <span>Count: <strong>{transactions.length}</strong></span>
        </div>
      </div>

      {loading ? <div>Loading...</div> : transactions.length === 0 ? (
        <div className="bg-blue-50 p-4 rounded-lg">Nothing here.</div>
      ) : (
        <>
          <div className="bg-white rounded-xl shadow-sm border overflow-hidden mb-6">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left p-3">Date</th>
                  <th className="text-left p-3">Type</th>
                  <th className="text-right p-3">Amount</th>
                  <th className="text-left p-3">Account</th>
                  <th className="text-left p-3">Category</th>
                  <th className="text-left p-3">Merchant</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map(tx => (
                  <tr key={tx.id} onClick={() => { setSelectedTx(tx.id); setSelectedCat('') }}
                    className={`border-b cursor-pointer hover:bg-gray-50 ${selectedTx === tx.id ? 'bg-blue-50' : ''}`}>
                    <td className="p-3">{tx.date}</td>
                    <td className="p-3">
                      <span className={`px-2 py-1 rounded text-xs ${
                        tx.kind === 'expense' ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
                      }`}>{tx.kind}</span>
                    </td>
                    <td className="p-3 text-right font-mono">{formatMoney(tx.amount)}</td>
                    <td className="p-3">{tx.account}</td>
                    <td className="p-3">{tx.category || <span className="text-gray-400">—</span>}</td>
                    <td className="p-3 truncate max-w-[200px]">{tx.merchant}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {selectedTx && selectedTransaction && (
            <div className="bg-white p-4 rounded-xl shadow-sm border">
              <div className="mb-4 pb-3 border-b">
                <div className="text-sm text-gray-500">Selected:</div>
                <div className="font-medium">{selectedTransaction.merchant}</div>
                <div className="text-sm text-gray-600">
                  {selectedTransaction.date} · {formatMoney(selectedTransaction.amount)} · {selectedTransaction.account}
                </div>
              </div>

              <div className="flex gap-4 items-end">
                <div className="flex-1">
                  <label className="block text-sm mb-1">Category</label>
                  <select value={selectedCat} onChange={e => setSelectedCat(e.target.value)} className="w-full p-2 border rounded-lg">
                    <option value="">Select category</option>
                    {flatCats.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </div>
                <button onClick={handleSetCat} disabled={!selectedCat} className="px-4 py-2 bg-blue-600 text-white rounded-lg disabled:opacity-50">
                  Set Category
                </button>
                <button onClick={handleDelete} className="px-4 py-2 bg-red-100 text-red-700 rounded-lg">
                  Delete
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
