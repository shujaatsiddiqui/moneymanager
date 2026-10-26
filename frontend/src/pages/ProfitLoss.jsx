import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getProfitLoss, getYtdProfitLoss } from '../api'
import { useMonth } from '../hooks'
import { formatMoney } from '../utils'
import { LoadingSpinner, MonthSelector } from '../components'

export default function ProfitLoss() {
  const { month, setMonth, changeMonth, monthOptions } = useMonth(24)
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [viewMode, setViewMode] = useState('monthly') // 'monthly' or 'ytd'
  const [businessFilter, setBusinessFilter] = useState(null) // null = all, true = business, false = personal
  const navigate = useNavigate()

  const year = parseInt(month.split('-')[0])

  useEffect(() => {
    setLoading(true)
    const fetchReport = viewMode === 'ytd'
      ? getYtdProfitLoss(year, businessFilter)
      : getProfitLoss(month, businessFilter)

    fetchReport
      .then(setReport)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [month, year, viewMode, businessFilter])

  const handleCategoryClick = (categoryId, categoryName) => {
    let url = `/transactions?month=${month}&category=${categoryId}&category_name=${encodeURIComponent(categoryName)}`
    if (businessFilter !== null) {
      url += `&is_business=${businessFilter}`
    }
    navigate(url)
  }

  if (loading) return <LoadingSpinner />
  if (!report) return <div className="text-red-500">Failed to load report</div>

  const { revenue, expenses, refunds, summary } = report

  return (
    <div>
      {/* Header with Month Navigation and Filters */}
      <div className="flex items-center justify-between mb-6">
        <MonthSelector
          month={month}
          monthOptions={monthOptions}
          onMonthChange={setMonth}
          onPrev={() => changeMonth(-1)}
          onNext={() => changeMonth(1)}
          title="Profit & Loss"
        />
        <div className="flex gap-4">
          {/* View Mode Toggle */}
          <div className="flex rounded-lg border bg-white">
            <button
              onClick={() => setViewMode('monthly')}
              className={`px-4 py-2 text-sm rounded-l-lg ${viewMode === 'monthly' ? 'bg-blue-600 text-white' : 'hover:bg-gray-100'}`}
            >
              Monthly
            </button>
            <button
              onClick={() => setViewMode('ytd')}
              className={`px-4 py-2 text-sm rounded-r-lg ${viewMode === 'ytd' ? 'bg-blue-600 text-white' : 'hover:bg-gray-100'}`}
            >
              YTD {year}
            </button>
          </div>
          {/* Business Filter */}
          <select
            value={businessFilter === null ? 'all' : businessFilter ? 'business' : 'personal'}
            onChange={(e) => {
              const val = e.target.value
              setBusinessFilter(val === 'all' ? null : val === 'business')
            }}
            className="px-3 py-2 border rounded-lg bg-white text-sm"
          >
            <option value="all">All Transactions</option>
            <option value="personal">Personal Only</option>
            <option value="business">Business Only</option>
          </select>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <SummaryCard
          label="Revenue"
          value={revenue.total}
          color="green"
        />
        <SummaryCard
          label="Operating Expenses"
          value={-expenses.operating.total}
          color="red"
        />
        <SummaryCard
          label="Refunds"
          value={refunds.total}
          color="blue"
        />
        <SummaryCard
          label="Net Income"
          value={summary.net_income}
          color={summary.net_income >= 0 ? 'green' : 'red'}
          highlight
        />
      </div>

      {/* Revenue Section */}
      <Section title="Revenue" total={revenue.total} color="green">
        {revenue.categories.length === 0 && revenue.uncategorized === 0 ? (
          <EmptyState message="No income recorded" />
        ) : (
          <>
            {revenue.categories.map((cat) => (
              <CategoryRow
                key={cat.category_id}
                category={cat}
                onClick={() => handleCategoryClick(cat.category_id, cat.category)}
              />
            ))}
            {revenue.uncategorized > 0 && (
              <div className="flex justify-between py-2 px-4 text-gray-500 italic">
                <span>Uncategorized</span>
                <span>{formatMoney(revenue.uncategorized)}</span>
              </div>
            )}
          </>
        )}
      </Section>

      {/* Operating Expenses Section */}
      <Section title="Operating Expenses" total={expenses.operating.total} color="red">
        {expenses.operating.categories.length === 0 && expenses.operating.uncategorized === 0 ? (
          <EmptyState message="No operating expenses" />
        ) : (
          <>
            {expenses.operating.categories.map((cat) => (
              <CategoryRow
                key={cat.category_id}
                category={cat}
                onClick={() => handleCategoryClick(cat.category_id, cat.category)}
              />
            ))}
            {expenses.operating.uncategorized > 0 && (
              <div className="flex justify-between py-2 px-4 text-gray-500 italic">
                <span>Uncategorized</span>
                <span>{formatMoney(expenses.operating.uncategorized)}</span>
              </div>
            )}
          </>
        )}
      </Section>

      {/* Gross Profit Row */}
      <div className="bg-gray-100 rounded-lg p-4 mb-6 flex justify-between items-center">
        <span className="font-semibold text-gray-700">Gross Profit</span>
        <span className={`font-bold text-lg ${summary.gross_profit >= 0 ? 'text-green-600' : 'text-red-600'}`}>
          {formatMoney(summary.gross_profit)}
        </span>
      </div>

      {/* Operating Income Row */}
      <div className="bg-blue-50 rounded-lg p-4 mb-6 flex justify-between items-center">
        <span className="font-semibold text-blue-700">Operating Income</span>
        <span className={`font-bold text-lg ${summary.operating_income >= 0 ? 'text-green-600' : 'text-red-600'}`}>
          {formatMoney(summary.operating_income)}
        </span>
      </div>

      {/* Refunds Section (if any) */}
      {refunds.total > 0 && (
        <Section title="Refunds (Expense Returns)" total={refunds.total} color="blue">
          {refunds.categories.map((cat) => (
            <CategoryRow
              key={cat.category_id}
              category={cat}
              onClick={() => handleCategoryClick(cat.category_id, cat.category)}
            />
          ))}
        </Section>
      )}

      {/* Non-Operating Expenses Section */}
      {expenses.non_operating.total > 0 && (
        <Section title="Non-Operating Expenses (Excluded from Budget)" total={expenses.non_operating.total} color="gray">
          {expenses.non_operating.categories.map((cat) => (
            <CategoryRow
              key={cat.category_id}
              category={cat}
              onClick={() => handleCategoryClick(cat.category_id, cat.category)}
            />
          ))}
        </Section>
      )}

      {/* Net Income */}
      <div className={`rounded-lg p-6 mt-6 flex justify-between items-center ${
        summary.net_income >= 0 ? 'bg-green-100' : 'bg-red-100'
      }`}>
        <span className={`font-bold text-xl ${summary.net_income >= 0 ? 'text-green-800' : 'text-red-800'}`}>
          Net Income
        </span>
        <span className={`font-bold text-2xl ${summary.net_income >= 0 ? 'text-green-700' : 'text-red-700'}`}>
          {formatMoney(summary.net_income)}
        </span>
      </div>
    </div>
  )
}

function SummaryCard({ label, value, color, highlight = false }) {
  const colorClasses = {
    green: 'text-green-600',
    red: 'text-red-600',
    blue: 'text-blue-600',
    gray: 'text-gray-600',
  }

  return (
    <div className={`bg-white rounded-xl shadow-sm border p-4 ${highlight ? 'ring-2 ring-blue-200' : ''}`}>
      <div className="text-sm text-gray-500 mb-1">{label}</div>
      <div className={`text-xl font-bold ${colorClasses[color]}`}>
        {formatMoney(value)}
      </div>
    </div>
  )
}

function Section({ title, total, color, children }) {
  const borderColors = {
    green: 'border-l-green-500',
    red: 'border-l-red-500',
    blue: 'border-l-blue-500',
    gray: 'border-l-gray-400',
  }

  const textColors = {
    green: 'text-green-600',
    red: 'text-red-600',
    blue: 'text-blue-600',
    gray: 'text-gray-600',
  }

  return (
    <div className={`bg-white rounded-xl shadow-sm border border-l-4 ${borderColors[color]} mb-6`}>
      <div className="flex justify-between items-center p-4 border-b">
        <h3 className="font-semibold text-gray-700">{title}</h3>
        <span className={`font-bold ${textColors[color]}`}>{formatMoney(total)}</span>
      </div>
      <div className="divide-y">{children}</div>
    </div>
  )
}

function CategoryRow({ category, onClick }) {
  return (
    <button
      onClick={onClick}
      className="w-full flex justify-between items-center py-3 px-4 hover:bg-gray-50 text-left"
    >
      <span>
        {category.emoji && <span className="mr-2">{category.emoji}</span>}
        {category.category}
      </span>
      <span className="font-medium">{formatMoney(category.amount)}</span>
    </button>
  )
}

function EmptyState({ message }) {
  return (
    <div className="py-4 px-4 text-gray-400 text-center italic">
      {message}
    </div>
  )
}
