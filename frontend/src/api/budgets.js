import { request } from './client'

/**
 * Get budget status for a month.
 * @param {string} month - Month in YYYY-MM format
 * @returns {Promise<Object>} Budget status with rows and totals
 */
export function getBudgetStatus(month) {
  return request('GET', `/budgets/status?month=${month}`)
}

/**
 * Set or update a budget.
 * @param {Object} data - {category_id, month, limit}
 * @returns {Promise<{id: number}>}
 */
export function setBudget(data) {
  return request('PUT', '/budgets', data)
}

/**
 * Delete a budget.
 * @param {number} categoryId - Category ID
 * @param {string} month - Month in YYYY-MM format
 * @returns {Promise<{ok: boolean}>}
 */
export function deleteBudget(categoryId, month) {
  return request('DELETE', `/budgets?category_id=${categoryId}&month=${month}`)
}

/**
 * Copy budgets from one month to another.
 * @param {string} fromMonth - Source month
 * @param {string} toMonth - Target month
 * @returns {Promise<{copied: number}>}
 */
export function copyBudgets(fromMonth, toMonth) {
  return request('POST', `/budgets/copy?from_month=${fromMonth}&to_month=${toMonth}`)
}
