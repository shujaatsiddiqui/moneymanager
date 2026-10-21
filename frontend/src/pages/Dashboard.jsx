import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api, formatMoney, getMonthOptions } from '../api'

export default function Dashboard({ month }) {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  useEffect(() => {
    setLoading(true)
    api.getBudgetStatus(month).then(setStatus).catch(console.error).finally(() => setLoading(false))
  }, [month])

  const handleCategoryClick = (categoryId, categoryName) => {
    navigate(`/transactions?month=${month}&category=${categoryId}&category_name=${encodeURIComponent(categoryName)}`)
  }

  const changeMonth = (direction) => {
    const [year, mon] = month.split('-').map(Number)
    let newYear = year, newMonth = mon + direction
    if (newMonth > 12) { newYear++; newMonth = 1 }
    if (newMonth < 1) { newYear--; newMonth = 12 }
    const newMonthStr = `${newYear}-${String(newMonth).padStart(2, '0')}`
    setSearchParams({ month: newMonthStr })
  }

  const monthOptions = getMonthOptions(24)

  if (loading) return <div className="text-gray-500">Loading...</div>
  if (!status) return <div className="text-red-500">Failed to load</div>

  return (
    <div>
      {/* Month Navigation */}
      <div className="flex items-center justify-between mb-6">
        <button onClick={() => changeMonth(-1)} className="px-3 py-2 bg-gray-100 rounded-lg hover:bg-gray-200">
          ← Prev
        </button>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-gray-800">Budget</h1>
          <select
            value={month}
            onChange={(e) => setSearchParams({ month: e.target.value })}
            className="text-2xl font-bold text-blue-600 bg-transparent border-none cursor-pointer"
          >
            {monthOptions.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>
        <button onClick={() => changeMonth(1)} className="px-3 py-2 bg-gray-100 rounded-lg hover:bg-gray-200">
          Next →
        </button>
      </div>

      {/* Income vs Expenses Summary */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <button
          onClick={() => navigate(`/transactions?month=${month}&type=income`)}
          className="bg-white p-4 rounded-xl shadow-sm border text-left hover:bg-green-50 transition-colors"
        >
          <div className="text-sm text-gray-500">Income</div>
          <div className="text-2xl font-bold text-green-600">{formatMoney(status.total_income)}</div>
        </button>
        <button
          onClick={() => navigate(`/transactions?month=${month}&type=expense`)}
          className="bg-white p-4 rounded-xl shadow-sm border text-left hover:bg-red-50 transition-colors"
        >
          <div className="text-sm text-gray-500">Expenses</div>
          <div className="text-2xl font-bold text-red-600">{formatMoney(status.total_expenses)}</div>
        </button>
        <div className="bg-white p-4 rounded-xl shadow-sm border">
          <div className="text-sm text-gray-500">Saved</div>
          <div className={`text-2xl font-bold ${status.saved >= 0 ? 'text-blue-600' : 'text-red-600'}`}>
            {formatMoney(status.saved)}
          </div>
        </div>
        <div className="bg-white p-4 rounded-xl shadow-sm border">
          <div className="text-sm text-gray-500">Savings Rate</div>
          <div className={`text-2xl font-bold ${status.savings_rate >= 0 ? 'text-blue-600' : 'text-red-600'}`}>
            {status.savings_rate}%
          </div>
        </div>
      </div>

      {/* Budget Summary Cards */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="bg-white p-4 rounded-xl shadow-sm border">
          <div className="text-sm text-gray-500">Budgeted</div>
          <div className="text-2xl font-bold">{formatMoney(status.total_limit)}</div>
        </div>
        <div className="bg-white p-4 rounded-xl shadow-sm border">
          <div className="text-sm text-gray-500">Spent</div>
          <div className="text-2xl font-bold">{formatMoney(status.total_spent)}</div>
        </div>
        <div className="bg-white p-4 rounded-xl shadow-sm border">
          <div className="text-sm text-gray-500">Left</div>
          <div className={`text-2xl font-bold ${status.total_left >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {formatMoney(status.total_left)}
          </div>
        </div>
      </div>

      {/* Budget Categories */}
      {status.rows.length === 0 ? (
        <div className="bg-blue-50 text-blue-700 p-4 rounded-lg">No budgets yet.</div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border">
          {status.rows.map((r) => {
            const pct = r.limit ? Math.min((r.spent / r.limit) * 100, 100) : 100
            const over = r.left < 0
            return (
              <div key={r.category_id} className="p-4 border-b last:border-b-0 hover:bg-gray-50">
                <div className="flex items-center justify-between mb-2">
                  <button onClick={() => handleCategoryClick(r.category_id, r.category)}
                    className="text-left font-medium hover:text-blue-600">
                    {r.emoji} {r.category}
                  </button>
                  <div className="flex gap-6 text-sm">
                    <span>{formatMoney(r.spent)}</span>
                    <span className="text-gray-400">of {formatMoney(r.limit)}</span>
                    <span className={over ? 'text-red-600' : 'text-green-600'}>
                      {over ? `⚠️ ${formatMoney(-r.left)} over` : `${formatMoney(r.left)} left`}
                    </span>
                  </div>
                </div>
                <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${over ? 'bg-red-500' : 'bg-blue-500'}`} style={{width:`${pct}%`}}/>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Footer Stats */}
      <div className="grid grid-cols-3 gap-4 mt-8">
        <button
          onClick={() => navigate(`/transactions?month=${month}&unbudgeted=true`)}
          className="bg-white p-4 rounded-xl shadow-sm border text-left hover:bg-orange-50 transition-colors"
        >
          <div className="text-sm text-gray-500">Unbudgeted</div>
          <div className="text-xl font-bold text-orange-600">{formatMoney(status.unbudgeted_spent)}</div>
        </button>
        <button
          onClick={() => navigate(`/transactions?month=${month}&uncategorized=true`)}
          className="bg-white p-4 rounded-xl shadow-sm border text-left hover:bg-red-50 transition-colors"
        >
          <div className="text-sm text-gray-500">Uncategorized</div>
          <div className="text-xl font-bold text-red-600">{formatMoney(status.uncategorized_spent)}</div>
        </button>
        <button
          onClick={() => navigate(`/transactions?month=${month}&excluded=true`)}
          className="bg-white p-4 rounded-xl shadow-sm border text-left hover:bg-gray-100 transition-colors"
        >
          <div className="text-sm text-gray-500">Excluded</div>
          <div className="text-xl font-bold text-gray-600">{formatMoney(status.excluded_spent)}</div>
        </button>
      </div>
    </div>
  )
}
