/**
 * Format a number as currency (USD).
 * @param {number|null} amount - The amount to format
 * @returns {string} Formatted currency string
 */
export function formatMoney(amount) {
  if (amount == null || isNaN(amount)) return '$0.00'
  const formatted = Math.abs(amount).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  return amount >= 0 ? `$${formatted}` : `-$${formatted}`
}

/**
 * Format a date string for display.
 * @param {string} dateStr - ISO date string
 * @returns {string} Formatted date
 */
export function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

/**
 * Format a month string (YYYY-MM) for display.
 * @param {string} month - Month in YYYY-MM format
 * @returns {string} Formatted month (e.g., "January 2026")
 */
export function formatMonth(month) {
  if (!month) return ''
  const [year, mon] = month.split('-')
  const date = new Date(year, parseInt(mon) - 1)
  return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
}
