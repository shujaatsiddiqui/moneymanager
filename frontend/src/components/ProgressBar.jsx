/**
 * Progress bar component.
 */
export default function ProgressBar({
  value,
  max = 100,
  color = 'blue',
  showLabel = false,
  className = '',
}) {
  const percentage = max > 0 ? Math.min((value / max) * 100, 100) : 0
  const isOver = value > max

  const colorClasses = {
    blue: 'bg-blue-500',
    green: 'bg-green-500',
    red: 'bg-red-500',
    orange: 'bg-orange-500',
    auto: isOver ? 'bg-red-500' : 'bg-blue-500',
  }

  return (
    <div className={className}>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${colorClasses[color] || colorClasses.blue}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showLabel && (
        <div className="text-xs text-gray-500 mt-1">
          {Math.round(percentage)}%
        </div>
      )}
    </div>
  )
}
