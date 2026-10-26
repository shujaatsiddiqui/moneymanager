import { request } from './client'

/**
 * Get all accounts with balances.
 * @returns {Promise<{accounts: Array, assets: number, liabilities: number, total: number}>}
 */
export function getAccounts() {
  return request('GET', '/accounts')
}

/**
 * Update an account.
 * @param {number} id - Account ID
 * @param {Object} data - Fields to update
 * @returns {Promise<{ok: boolean}>}
 */
export function updateAccount(id, data) {
  return request('PATCH', `/accounts/${id}`, data)
}

/**
 * Get credit card due dates.
 * @returns {Promise<Array>} Credit cards with due date info
 */
export function getCreditCardDues() {
  return request('GET', '/accounts/credit-card-dues')
}
