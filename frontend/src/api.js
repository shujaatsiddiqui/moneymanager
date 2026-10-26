// Re-export everything from the new api/ directory structure
// This file maintains backward compatibility with old imports

export * from './api/index.js'
export { api } from './api/index.js'

// Legacy utilities (these should be moved to utils/ eventually)
export function formatMoney(amount) {
  if (amount == null || isNaN(amount)) return '$0.00'
  return amount >= 0
    ? `$${amount.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}`
    : `-$${Math.abs(amount).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}`
}

export function getMonthOptions(n = 18) {
  const options = []
  const now = new Date()
  let year = now.getFullYear()
  let month = now.getMonth() + 1
  for (let i = 0; i < n; i++) {
    options.push(`${year}-${String(month).padStart(2, '0')}`)
    month--
    if (month === 0) { year--; month = 12 }
  }
  return options
}
