import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, formatMoney, getMonthOptions } from '../api'

export default function Transactions({ month, categories, accounts }) {
  const [searchParams, setSearchParams] = useSearchParams()
  const [transactions, setTransactions] = useState([])
  const [loading, setLoading] = useState(true)
  const [onlyUncat, setOnlyUncat] = useState(false)
  const [selectedTxIds, setSelectedTxIds] = useState([])
  const [selectedCat, setSelectedCat] = useState('')
  const [createRule, setCreateRule] = useState(true)
  const [sortField, setSortField] = useState('date')
  const [sortDir, setSortDir] = useState('desc')
  const [filters, setFilters] = useState({
    type: '',
    account: '',
    category: '',
    merchant: '',
    minAmount: '',
    maxAmount: '',
  })

  const categoryId = searchParams.get('category')
  const categoryName = searchParams.get('category_name')
  const accountId = searchParams.get('account')
  const accountName = searchParams.get('account_name')

  const loadTransactions = async () => {
    setLoading(true)
    const params = { uncategorized: onlyUncat }
    if (!accountId) params.month = month  // Only filter by month if not filtering by account
    if (categoryId) params.category_id = categoryId
    if (accountId) params.account_id = accountId
    try {
      setTransactions(await api.getTransactions(params))
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadTransactions() }, [month, categoryId, accountId, onlyUncat])

  const clearFilter = () => {
    const params = new URLSearchParams(searchParams)
    params.delete('category')
    params.delete('category_name')
    params.delete('account')
    params.delete('account_name')
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
    if (selectedTxIds.length === 0 || !selectedCat) return

    const categoryId = parseInt(selectedCat)
    const selectedTxs = transactions.filter(t => selectedTxIds.includes(t.id))

    // Update all selected transactions
    for (const tx of selectedTxs) {
      await api.updateTransaction(tx.id, { category_id: categoryId })
    }

    // Create rules if checkbox is checked
    if (createRule) {
      const seenPatterns = new Set()
      for (const tx of selectedTxs) {
        try {
          const { pattern } = await api.suggestPattern(tx.merchant)
          if (pattern && pattern.length >= 3 && !seenPatterns.has(pattern.toLowerCase())) {
            seenPatterns.add(pattern.toLowerCase())
            await api.createRule({ pattern, category_id: categoryId, priority: 100 })
          }
        } catch (e) {
          // Fallback: use first word
          const pattern = tx.merchant.split(/\s+/)[0]
          if (pattern && pattern.length >= 3 && !seenPatterns.has(pattern.toLowerCase())) {
            seenPatterns.add(pattern.toLowerCase())
            try {
              await api.createRule({ pattern, category_id: categoryId, priority: 100 })
            } catch (e) {
              // Rule might already exist, ignore
            }
          }
        }
      }
    }

    await loadTransactions()
    setSelectedTxIds([])
    setSelectedCat('')
  }

  const handleDelete = async () => {
    if (selectedTxIds.length === 0 || !confirm(`Delete ${selectedTxIds.length} transaction(s)?`)) return
    for (const id of selectedTxIds) {
      await api.deleteTransaction(id)
    }
    setTransactions(transactions.filter(t => !selectedTxIds.includes(t.id)))
    setSelectedTxIds([])
  }

  const toggleSelect = (id) => {
    setSelectedTxIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    )
  }

  const selectedTransactions = transactions.filter(t => selectedTxIds.includes(t.id))

  const flatCats = []
  categories.forEach(c => {
    flatCats.push({ id: c.id, name: `${c.emoji} ${c.name}` })
    c.children?.forEach(s => flatCats.push({ id: s.id, name: `  └ ${s.name}` }))
  })

  const monthOptions = getMonthOptions(24)

  // Apply filters
  const filteredTransactions = transactions.filter(tx => {
    if (filters.type && tx.kind !== filters.type) return false
    if (filters.account && !tx.account?.toLowerCase().includes(filters.account.toLowerCase())) return false
    if (filters.category && !tx.category?.toLowerCase().includes(filters.category.toLowerCase())) return false
    if (filters.merchant && !tx.merchant?.toLowerCase().includes(filters.merchant.toLowerCase())) return false
    if (filters.minAmount && tx.amount < parseFloat(filters.minAmount)) return false
    if (filters.maxAmount && tx.amount > parseFloat(filters.maxAmount)) return false
    return true
  })

  // Apply sorting
  const sortedTransactions = [...filteredTransactions].sort((a, b) => {
    let aVal, bVal
    switch (sortField) {
      case 'date':
        aVal = a.date || ''
        bVal = b.date || ''
        break
      case 'type':
        aVal = a.kind || ''
        bVal = b.kind || ''
        break
      case 'amount':
        aVal = a.amount || 0
        bVal = b.amount || 0
        break
      case 'account':
        aVal = a.account || ''
        bVal = b.account || ''
        break
      case 'category':
        aVal = a.category || ''
        bVal = b.category || ''
        break
      case 'merchant':
        aVal = a.merchant || ''
        bVal = b.merchant || ''
        break
      default:
        return 0
    }
    if (aVal < bVal) return sortDir === 'asc' ? -1 : 1
    if (aVal > bVal) return sortDir === 'asc' ? 1 : -1
    return 0
  })

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDir('asc')
    }
  }

  const updateFilter = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }))
  }

  const toggleSelectAll = () => {
    if (selectedTxIds.length === sortedTransactions.length) {
      setSelectedTxIds([])
    } else {
      setSelectedTxIds(sortedTransactions.map(t => t.id))
    }
  }

  const SortHeader = ({ field, children, className = '' }) => (
    <th
      className={`p-3 cursor-pointer hover:bg-gray-100 select-none ${className}`}
      onClick={() => handleSort(field)}
    >
      <div className="flex items-center gap-1">
        {children}
        {sortField === field && (
          <span className="text-blue-600">{sortDir === 'asc' ? '▲' : '▼'}</span>
        )}
      </div>
    </th>
  )

  // Calculate totals from filtered transactions
  const totalExpense = sortedTransactions.filter(t => t.kind === 'expense').reduce((a, t) => a + t.amount, 0)
  const totalIncome = sortedTransactions.filter(t => t.kind === 'income').reduce((a, t) => a + t.amount, 0)

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
          {accountName && <span className="text-xl text-gray-500">· {accountName}</span>}
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
          {(categoryName || accountName) && (
            <button onClick={clearFilter} className="px-3 py-1 text-sm bg-gray-100 rounded-lg hover:bg-gray-200">
              ✕ Clear filter
            </button>
          )}
        </div>
        <div className="flex gap-4 text-sm">
          <span>Expenses: <strong className="text-red-600">{formatMoney(totalExpense)}</strong></span>
          <span>Income: <strong className="text-green-600">{formatMoney(totalIncome)}</strong></span>
          <span>Count: <strong>{sortedTransactions.length}</strong>{sortedTransactions.length !== transactions.length && ` / ${transactions.length}`}</span>
        </div>
      </div>

      {loading ? <div>Loading...</div> : transactions.length === 0 ? (
        <div className="bg-blue-50 p-4 rounded-lg">Nothing here.</div>
      ) : (
        <>
          <div className="bg-white rounded-xl shadow-sm border overflow-hidden mb-6">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr className="border-b">
                  <th className="p-3 w-8">
                    <input
                      type="checkbox"
                      checked={selectedTxIds.length === sortedTransactions.length && sortedTransactions.length > 0}
                      onChange={toggleSelectAll}
                      className="rounded"
                    />
                  </th>
                  <SortHeader field="date" className="text-left">Date</SortHeader>
                  <SortHeader field="type" className="text-left">Type</SortHeader>
                  <SortHeader field="amount" className="text-right">Amount</SortHeader>
                  <SortHeader field="account" className="text-left">Account</SortHeader>
                  <SortHeader field="category" className="text-left">Category</SortHeader>
                  <SortHeader field="merchant" className="text-left">Merchant</SortHeader>
                </tr>
                <tr className="border-b bg-gray-50">
                  <td className="p-2"></td>
                  <td className="p-2 text-xs text-gray-500">via month</td>
                  <td className="p-2">
                    <select
                      value={filters.type}
                      onChange={e => updateFilter('type', e.target.value)}
                      className="w-full p-1 text-xs border rounded"
                    >
                      <option value="">All</option>
                      <option value="expense">Expense</option>
                      <option value="income">Income</option>
                      <option value="transfer">Transfer</option>
                    </select>
                  </td>
                  <td className="p-2">
                    <div className="flex gap-1">
                      <input
                        type="number"
                        placeholder="Min"
                        value={filters.minAmount}
                        onChange={e => updateFilter('minAmount', e.target.value)}
                        className="w-16 p-1 text-xs border rounded"
                      />
                      <input
                        type="number"
                        placeholder="Max"
                        value={filters.maxAmount}
                        onChange={e => updateFilter('maxAmount', e.target.value)}
                        className="w-16 p-1 text-xs border rounded"
                      />
                    </div>
                  </td>
                  <td className="p-2">
                    <input
                      type="text"
                      placeholder="Filter..."
                      value={filters.account}
                      onChange={e => updateFilter('account', e.target.value)}
                      className="w-full p-1 text-xs border rounded"
                    />
                  </td>
                  <td className="p-2">
                    <input
                      type="text"
                      placeholder="Filter..."
                      value={filters.category}
                      onChange={e => updateFilter('category', e.target.value)}
                      className="w-full p-1 text-xs border rounded"
                    />
                  </td>
                  <td className="p-2">
                    <input
                      type="text"
                      placeholder="Filter..."
                      value={filters.merchant}
                      onChange={e => updateFilter('merchant', e.target.value)}
                      className="w-full p-1 text-xs border rounded"
                    />
                  </td>
                </tr>
              </thead>
              <tbody>
                {sortedTransactions.map(tx => (
                  <tr key={tx.id}
                    onClick={() => toggleSelect(tx.id)}
                    className={`border-b cursor-pointer hover:bg-gray-50 ${selectedTxIds.includes(tx.id) ? 'bg-blue-50' : ''}`}>
                    <td className="p-3">
                      <input
                        type="checkbox"
                        checked={selectedTxIds.includes(tx.id)}
                        onChange={() => {}}
                        onClick={e => e.stopPropagation()}
                        className="rounded pointer-events-none"
                      />
                    </td>
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

          {selectedTxIds.length > 0 && (
            <div className="bg-white p-4 rounded-xl shadow-sm border">
              <div className="mb-4 pb-3 border-b">
                <div className="text-sm text-gray-500">Selected: <strong>{selectedTxIds.length}</strong> transaction(s)</div>
                {selectedTxIds.length <= 3 && selectedTransactions.map(tx => (
                  <div key={tx.id} className="text-sm text-gray-600 truncate">
                    {tx.merchant} · {formatMoney(tx.amount)}
                  </div>
                ))}
                {selectedTxIds.length > 3 && (
                  <div className="text-sm text-gray-500">
                    Total: {formatMoney(selectedTransactions.reduce((sum, tx) => sum + tx.amount, 0))}
                  </div>
                )}
              </div>

              <div className="flex gap-4 items-end">
                <div className="flex-1">
                  <label className="block text-sm mb-1">Category</label>
                  <select value={selectedCat} onChange={e => setSelectedCat(e.target.value)} className="w-full p-2 border rounded-lg">
                    <option value="">Select category</option>
                    {flatCats.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                  <label className="flex items-center gap-2 mt-2 text-sm text-gray-600">
                    <input type="checkbox" checked={createRule} onChange={e => setCreateRule(e.target.checked)} className="rounded" />
                    Create rule for next time
                  </label>
                </div>
                <button onClick={handleSetCat} disabled={!selectedCat} className="px-4 py-2 bg-blue-600 text-white rounded-lg disabled:opacity-50">
                  Set Category
                </button>
                <button onClick={handleDelete} className="px-4 py-2 bg-red-100 text-red-700 rounded-lg">
                  Delete
                </button>
                <button onClick={() => setSelectedTxIds([])} className="px-4 py-2 bg-gray-100 rounded-lg">
                  Clear
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
