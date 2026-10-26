/**
 * Get an array of month options (YYYY-MM format).
 * @param {number} count - Number of months to generate (default 18)
 * @returns {string[]} Array of month strings
 */
export function getMonthOptions(count = 18) {
  const options = []
  const now = new Date()
  let year = now.getFullYear()
  let month = now.getMonth() + 1

  for (let i = 0; i < count; i++) {
    options.push(`${year}-${String(month).padStart(2, '0')}`)
    month--
    if (month === 0) {
      year--
      month = 12
    }
  }

  return options
}

/**
 * Get the current month in YYYY-MM format.
 * @returns {string} Current month
 */
export function getCurrentMonth() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

/**
 * Navigate to next or previous month.
 * @param {string} month - Current month in YYYY-MM format
 * @param {number} direction - 1 for next, -1 for previous
 * @returns {string} New month in YYYY-MM format
 */
export function changeMonth(month, direction) {
  const [year, mon] = month.split('-').map(Number)
  let newYear = year
  let newMonth = mon + direction

  if (newMonth > 12) {
    newYear++
    newMonth = 1
  }
  if (newMonth < 1) {
    newYear--
    newMonth = 12
  }

  return `${newYear}-${String(newMonth).padStart(2, '0')}`
}
