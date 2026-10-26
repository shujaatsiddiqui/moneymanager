/**
 * Message/alert component for success/error feedback.
 */
export default function Message({ type = 'info', children, onDismiss = null }) {
  const typeClasses = {
    success: 'bg-green-50 text-green-700 border-green-200',
    error: 'bg-red-50 text-red-700 border-red-200',
    warning: 'bg-yellow-50 text-yellow-700 border-yellow-200',
    info: 'bg-blue-50 text-blue-700 border-blue-200',
  }

  return (
    <div className={`p-4 rounded-lg border ${typeClasses[type] || typeClasses.info}`}>
      <div className="flex items-center justify-between">
        <span>{children}</span>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="ml-4 text-current opacity-50 hover:opacity-100"
          >
            ×
          </button>
        )}
      </div>
    </div>
  )
}
