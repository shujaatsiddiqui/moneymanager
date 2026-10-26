import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getBudgetStatus, getCreditCardDues } from '../api'
import { useMonth } from '../hooks'
import { formatMoney } from '../utils'
import { LoadingSpinner, StatCard, MonthSelector, ProgressBar } from '../components'

export default function Dashboard() {
  const { month, setMonth, changeMonth, monthOptions } = useMonth(24)
  const [status, setStatus] = useState(null)
  const [cardDues, setCardDues] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    setLoading(true)
    Promise.all([
      getBudgetStatus(month),
      getCreditCardDues()
    ])
      .then(([budgetData, duesData]) => {
        setStatus(budgetData)
        setCardDues(duesData)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [month])

  const handleCategoryClick = (categoryId, categoryName) => {
    navigate(`/transactions?month=${month}&category=${categoryId}&category_name=${encodeURIComponent(categoryName)}`)
  }

  if (loading) return <LoadingSpinner />
  if (!status) return <div className="text-red-500">Failed to load</div>

  // Helper functions for card dues
  const getCardBgColor = (card) => {
    if (!card.due_day) return 'bg-gray-100'
    if (card.is_overdue || card.days_until_due <= 1) return 'bg-red-100'
    if (card.days_until_due <= 3) return 'bg-orange-100'
    return 'bg-emerald-200'
  }

  const getDueText = (card) => {
    if (!card.due_day) return 'No due date'
    if (card.is_overdue) return 'OVERDUE'
    if (card.days_until_due === 0) return 'Due TODAY'
    if (card.days_until_due === 1) return 'Tomorrow'
    return `${card.days_until_due} days`
  }

  const getDueTextColor = (card) => {
    if (!card.due_day) return 'text-gray-500'
    if (card.is_overdue || card.days_until_due <= 1) return 'text-red-700'
    if (card.days_until_due <= 3) return 'text-orange-700'
    return 'text-green-700'
  }

  return (
    <div>
      {/* Credit Card Payments Due - Top Row */}
      {cardDues.length > 0 && (
        <div className="mb-6">
          <div className="flex items-center justify-center gap-4 overflow-x-auto pb-2">
            {cardDues.map((card) => (
              <div
                key={card.id}
                onClick={() => navigate(`/transactions?account=${card.id}&account_name=${encodeURIComponent(card.name)}`)}
                className={`flex-shrink-0 rounded-xl shadow-sm border p-4 min-w-[200px] text-center cursor-pointer hover:opacity-80 transition-opacity ${getCardBgColor(card)}`}>
                <div className="text-sm text-gray-600 truncate font-medium">{card.name}</div>
                <div className={`text-xl font-bold ${card.balance < 0 ? 'text-red-600' : 'text-gray-900'}`}>
                  {formatMoney(Math.abs(card.balance))}
                </div>
                {card.statement_day && (
                  <div className="text-xs text-gray-500">
                    Stmt: {card.statement_day}th
                  </div>
                )}
                <div className={`text-sm font-semibold ${getDueTextColor(card)}`}>
                  {getDueText(card)}
                  {card.next_due_date && (
                    <span className="text-gray-500 font-normal ml-1">
                      ({new Date(card.next_due_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })})
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

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
