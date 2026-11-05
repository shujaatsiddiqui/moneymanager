import { useState, useEffect, Fragment } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, getMonthOptions } from '../api'
import { formatMoney } from '../utils'

export default function Budgets({ month: defaultMonth, categories }) {
  const [searchParams, setSearchParams] = useSearchParams()
  const monthParam = searchParams.get('month')
  const month = monthParam || defaultMonth
  const [status, setStatus] = useState(null)
  const [limits, setLimits] = useState({})
  const [loading, setLoading] = useState(true)
  const [copyFrom, setCopyFrom] = useState('')
  // Initialize all parents with children as collapsed
  const [collapsed, setCollapsed] = useState(() => {
    const initial = {}
    categories.filter(c => !c.exclude_from_budget && c.children?.length).forEach(c => {
      initial[c.id] = true
    })
    return initial
  })

  useEffect(() => {
    setLoading(true)
    api.getBudgetStatus(month).then(data => {
      setStatus(data)
      const cur = {}; data.rows.forEach(r => cur[r.category_id] = r.limit)
      setLimits(cur)
    }).finally(() => setLoading(false))
  }, [month])

  // Filter to budgetable expense categories only (exclude income categories)
  const budgetable = categories.filter(c => !c.exclude_from_budget && c.kind !== 'income')

  // Flatten for saving
  const allCategories = []
  budgetable.forEach(parent => {
    allCategories.push(parent)
    if (parent.children) {
      parent.children.forEach(child => allCategories.push({ ...child, emoji: '' }))
    }
  })

  const toggleCollapse = (parentId) => {
    setCollapsed(prev => ({ ...prev, [parentId]: !prev[parentId] }))
  }

  const handleSave = async () => {
    const orig = {}; status.rows.forEach(r => orig[r.category_id] = r.limit)
    for (const c of allCategories) {
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

  const changeMonth = (direction) => {
    const [year, mon] = month.split('-').map(Number)
    let newYear = year, newMonth = mon + direction
    if (newMonth > 12) { newYear++; newMonth = 1 }
    if (newMonth < 1) { newYear--; newMonth = 12 }
    const newMonthStr = `${newYear}-${String(newMonth).padStart(2, '0')}`
    setSearchParams({ month: newMonthStr })
  }

  const setMonth = (newMonth) => {
    setSearchParams({ month: newMonth })
  }

  const monthOptions = getMonthOptions(24)

  // Calculate parent totals: parent budget + all children budgets
  const getParentTotal = (parent) => {
    const parentBudget = limits[parent.id] || 0
    const childrenTotal = (parent.children || []).reduce((sum, c) => sum + (limits[c.id] || 0), 0)
    return parentBudget + childrenTotal
  }

  if (loading) return <div>Loading...</div>

  return (
    <div>
      {/* Month Navigation */}
      <div className="flex items-center justify-between mb-6">
        <button onClick={() => changeMonth(-1)} className="px-3 py-2 bg-gray-100 rounded-lg hover:bg-gray-200">
          ← Prev
        </button>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-gray-800">Budgets</h1>
          <select
            value={month}
            onChange={(e) => setMonth(e.target.value)}
            className="text-2xl font-bold text-blue-600 bg-transparent border-none cursor-pointer"
          >
            {monthOptions.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>
        <button onClick={() => changeMonth(1)} className="px-3 py-2 bg-gray-100 rounded-lg hover:bg-gray-200">
          Next →
        </button>
      </div>

      {/* Total Budget Summary */}
      <div className="bg-gray-100 rounded-xl p-4 mb-6">
        <div className="flex justify-between items-center">
          <span className="font-semibold">Total Budget</span>
          <span className="text-xl font-bold">
            {formatMoney(Object.values(limits).reduce((sum, v) => sum + (v || 0), 0))}
          </span>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border mb-6">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left p-3 w-8"></th>
              <th className="text-left p-3">Category</th>
              <th className="text-right p-3 w-40">Limit</th>
              <th className="text-right p-3 w-32">Total</th>
            </tr>
          </thead>
          <tbody>
            {budgetable.map(parent => {
              const children = parent.children || []
              const hasChildren = children.length > 0
              const isCollapsed = collapsed[parent.id]
              const parentTotal = getParentTotal(parent)

              return (
                <Fragment key={parent.id}>
                  {/* Parent row */}
                  <tr className="border-b bg-gray-100 font-medium">
                    <td className="p-3 text-center">
                      {hasChildren && (
                        <button
                          onClick={() => toggleCollapse(parent.id)}
                          className="text-gray-500 hover:text-gray-700 w-6 h-6"
                        >
                          {isCollapsed ? '▶' : '▼'}
                        </button>
                      )}
                    </td>
                    <td className="p-3">
                      {parent.emoji} {parent.name}
                      {hasChildren && (
                        <span className="text-xs text-gray-400 ml-2">
                          ({children.length} subcategories)
                        </span>
                      )}
                    </td>
                    <td className="p-3 text-right">
                      <input
                        type="number"
                        step="10"
                        min="0"
                        value={limits[parent.id] || ''}
                        onChange={e => setLimits({...limits, [parent.id]: parseFloat(e.target.value) || 0})}
                        className="w-32 p-2 border rounded-lg text-right"
                        placeholder="$0"
                      />
                    </td>
                    <td className="p-3 text-right font-semibold">
                      {formatMoney(parentTotal)}
                    </td>
                  </tr>

                  {/* Children rows */}
                  {hasChildren && !isCollapsed && children.map(child => (
                    <tr key={child.id} className="border-b bg-white hover:bg-gray-50">
                      <td className="p-3"></td>
                      <td className="p-3 pl-10">
                        <span className="text-gray-400 mr-2">└</span>
                        {child.name}
                      </td>
                      <td className="p-3 text-right">
                        <input
                          type="number"
                          step="10"
                          min="0"
                          value={limits[child.id] || ''}
                          onChange={e => setLimits({...limits, [child.id]: parseFloat(e.target.value) || 0})}
                          className="w-32 p-2 border rounded-lg text-right"
                          placeholder="$0"
                        />
                      </td>
                      <td className="p-3 text-right text-gray-500">
                        {formatMoney(limits[child.id] || 0)}
                      </td>
                    </tr>
                  ))}
                </Fragment>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Actions */}
      <div className="flex gap-4 flex-wrap">
        <button onClick={handleSave} className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          Save
        </button>
        <select value={copyFrom} onChange={e => setCopyFrom(e.target.value)} className="p-2 border rounded-lg">
          <option value="">Copy from...</option>
          {getMonthOptions().filter(m => m !== month).map(m => <option key={m} value={m}>{m}</option>)}
        </select>
        <button
          onClick={handleCopy}
          disabled={!copyFrom}
          className="px-4 py-2 bg-gray-100 border rounded-lg disabled:opacity-50 hover:bg-gray-200"
        >
          Copy
        </button>
        <button
          onClick={() => setCollapsed({})}
          className="px-4 py-2 bg-gray-100 border rounded-lg hover:bg-gray-200"
        >
          Expand All
        </button>
        <button
          onClick={() => {
            const all = {}
            budgetable.forEach(p => { if (p.children?.length) all[p.id] = true })
            setCollapsed(all)
          }}
          className="px-4 py-2 bg-gray-100 border rounded-lg hover:bg-gray-200"
        >
          Collapse All
        </button>
      </div>
    </div>
  )
}
