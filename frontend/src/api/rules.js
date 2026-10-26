import { request } from './client'

/**
 * Get all categorization rules.
 * @returns {Promise<Array>}
 */
export function getRules() {
  return request('GET', '/rules')
}

/**
 * Create a new rule.
 * @param {Object} data - Rule data
 * @returns {Promise<{id: number}>}
 */
export function createRule(data) {
  return request('POST', '/rules', data)
}

/**
 * Delete a rule.
 * @param {number} id - Rule ID
 * @returns {Promise<{ok: boolean}>}
 */
export function deleteRule(id) {
  return request('DELETE', `/rules/${id}`)
}

/**
 * Apply all rules to uncategorized transactions.
 * @returns {Promise<{categorized: number}>}
 */
export function applyRules() {
  return request('POST', '/rules/apply')
}

/**
 * Suggest a rule pattern for a description.
 * @param {string} description - Transaction description
 * @returns {Promise<{pattern: string|null}>}
 */
export function suggestPattern(description) {
  return request('GET', `/rules/suggest-pattern?description=${encodeURIComponent(description)}`)
}
