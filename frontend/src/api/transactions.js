import { request, buildQuery } from './client'

/**
 * Get transactions with filters.
 * @param {Object} params - Query parameters
 * @returns {Promise<Array>}
 */
export function getTransactions(params = {}) {
  const query = buildQuery(params)
  return request('GET', `/transactions?${query}`)
}

/**
 * Create a new transaction.
 * @param {Object} data - Transaction data
 * @returns {Promise<Object>}
 */
export function createTransaction(data) {
  return request('POST', '/transactions', data)
}

/**
 * Update a transaction.
 * @param {number} id - Transaction ID
 * @param {Object} data - Fields to update
 * @returns {Promise<Object>}
 */
export function updateTransaction(id, data) {
  return request('PATCH', `/transactions/${id}`, data)
}

/**
 * Delete a transaction.
 * @param {number} id - Transaction ID
 * @returns {Promise<{ok: boolean}>}
 */
export function deleteTransaction(id) {
  return request('DELETE', `/transactions/${id}`)
}

/**
 * Detect and mark transfers in existing transactions.
 * @returns {Promise<{updated: number}>}
 */
export function detectTransfers() {
  return request('POST', '/transactions/detect-transfers')
}
