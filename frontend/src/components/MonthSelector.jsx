/**
 * Month selector with prev/next navigation.
 */
export default function MonthSelector({
  month,
  monthOptions,
  onMonthChange,
  onPrev,
  onNext,
  title = null,
  className = '',
}) {
  return (
    <div className={`flex items-center justify-between ${className}`}>
      <button
        onClick={onPrev}
        className="px-3 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
      >
        ← Prev
      </button>

      <div className="flex items-center gap-3">
        {title && <h1 className="text-2xl font-bold text-gray-800">{title}</h1>}
        <select
          value={month}
          onChange={(e) => onMonthChange(e.target.value)}
          className="text-2xl font-bold text-blue-600 bg-transparent border-none cursor-pointer focus:outline-none"
        >
          {monthOptions.map(m => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
      </div>

      <button
        onClick={onNext}
        className="px-3 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
      >
        Next →
      </button>
    </div>
  )
}
