/**
 * Statistic card component for displaying metrics.
 */
export default function StatCard({
  label,
  value,
  color = 'default',
  onClick = null,
  className = '',
}) {
  const colorClasses = {
    default: 'text-gray-800',
    green: 'text-green-600',
    red: 'text-red-600',
    blue: 'text-blue-600',
    orange: 'text-orange-600',
    gray: 'text-gray-600',
  }

  const hoverClasses = onClick ? {
    default: 'hover:bg-gray-50',
    green: 'hover:bg-green-50',
    red: 'hover:bg-red-50',
    blue: 'hover:bg-blue-50',
    orange: 'hover:bg-orange-50',
    gray: 'hover:bg-gray-100',
  } : {}

  const Component = onClick ? 'button' : 'div'
  const hoverClass = onClick ? hoverClasses[color] || '' : ''

  return (
    <Component
      onClick={onClick}
      className={`bg-white p-4 rounded-xl shadow-sm border text-left transition-colors ${hoverClass} ${className}`}
    >
      <div className="text-sm text-gray-500">{label}</div>
      <div className={`text-2xl font-bold ${colorClasses[color] || colorClasses.default}`}>
        {value}
      </div>
    </Component>
  )
}
