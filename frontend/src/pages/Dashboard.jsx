import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getBudgetStatus } from '../api'
import { useMonth } from '../hooks'
import { formatMoney } from '../utils'
import { LoadingSpinner, StatCard, MonthSelector, ProgressBar } from '../components'

export default function Dashboard() {
  const { month, setMonth, changeMonth, monthOptions } = useMonth(24)
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    setLoading(true)
    getBudgetStatus(month)
      .then(setStatus)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [month])

  const handleCategoryClick = (categoryId, categoryName) => {
    navigate(`/transactions?month=${month}&category=${categoryId}&category_name=${encodeURIComponent(categoryName)}`)
  }

  if (loading) return <LoadingSpinner />
  if (!status) return <div className="text-red-500">Failed to load</div>

  return (
    <div>
      {/* Month Navigation */}
      <MonthSelector
        month={month}
        monthOptions={monthOptions}
        onMonthChange={setMonth}
        onPrev={() => changeMonth(-1)}
        onNext={() => changeMonth(1)}
        title="Budget"
        className="mb-6"
      />

      {/* Income vs Expenses Summary */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <StatCard
          label="Income"
          value={formatMoney(status.total_income)}
          color="green"
          onClick={() => navigate(`/transactions?month=${month}&type=income`)}
        />
        <StatCard
          label="Expenses"
          value={formatMoney(status.total_expenses)}
          color="red"
          onClick={() => navigate(`/transactions?month=${month}&type=expense`)}
        />
        <StatCard
          label="Saved"
          value={formatMoney(status.saved)}
          color={status.saved >= 0 ? 'blue' : 'red'}
        />
        <StatCard
          label="Savings Rate"
          value={`${status.savings_rate}%`}
          color={status.savings_rate >= 0 ? 'blue' : 'red'}
        />
      </div>

      {/* Budget Summary Cards */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <StatCard label="Budgeted" value={formatMoney(status.total_limit)} />
        <StatCard label="Spent" value={formatMoney(status.total_spent)} />
        <StatCard
          label="Left"
          value={formatMoney(status.total_left)}
          color={status.total_left >= 0 ? 'green' : 'red'}
        />
      </div>

      {/* Budget Categories */}
      {status.rows.length === 0 ? (
        <div className="bg-blue-50 text-blue-700 p-4 rounded-lg">No budgets yet.</div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border">
          {status.rows.map((r) => {
            const over = r.left < 0
            return (
              <div key={r.category_id} className="p-4 border-b last:border-b-0 hover:bg-gray-50">
                <div className="flex items-center justify-between mb-2">
                  <button
                    onClick={() => handleCategoryClick(r.category_id, r.category)}
                    className="text-left font-medium hover:text-blue-600"
                  >
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
                <ProgressBar value={r.spent} max={r.limit} color="auto" />
              </div>
            )
          })}
        </div>
      )}

      {/* Footer Stats */}
      <div className="grid grid-cols-3 gap-4 mt-8">
        <StatCard
          label="Unbudgeted"
          value={formatMoney(status.unbudgeted_spent)}
          color="orange"
          onClick={() => navigate(`/transactions?month=${month}&unbudgeted=true`)}
        />
        <StatCard
          label="Uncategorized"
          value={formatMoney(status.uncategorized_spent)}
          color="red"
          onClick={() => navigate(`/transactions?month=${month}&uncategorized=true`)}
        />
        <StatCard
          label="Excluded"
          value={formatMoney(status.excluded_spent)}
          color="gray"
          onClick={() => navigate(`/transactions?month=${month}&excluded=true`)}
        />
      </div>
    </div>
  )
}
