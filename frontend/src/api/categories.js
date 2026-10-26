import { request } from './client'

/**
 * Get all categories (hierarchical tree).
 * @returns {Promise<Array>}
 */
export function getCategories() {
  return request('GET', '/categories')
}

/**
 * Create a new category.
 * @param {Object} data - Category data
 * @returns {Promise<{id: number}>}
 */
export function createCategory(data) {
  return request('POST', '/categories', data)
}

/**
 * Update a category.
 * @param {number} id - Category ID
 * @param {Object} data - Fields to update
 * @returns {Promise<{ok: boolean}>}
 */
export function updateCategory(id, data) {
  return request('PATCH', `/categories/${id}`, data)
}

/**
 * Delete a category (must have no transactions).
 * @param {number} id - Category ID
 * @returns {Promise<{ok: boolean}>}
 */
export function deleteCategory(id) {
  return request('DELETE', `/categories/${id}`)
}

/**
 * Delete a category and all its subcategories.
 * @param {number} id - Category ID
 * @returns {Promise<{ok: boolean, deleted: number}>}
 */
export function deleteCategoryCascade(id) {
  return request('DELETE', `/categories/${id}/cascade`)
}

/**
 * Get transaction counts for a category and its children.
 * @param {number} id - Category ID
 * @returns {Promise<{categories: Array, total: number, child_count: number}>}
 */
export function getCategoryTransactions(id) {
  return request('GET', `/categories/${id}/transactions`)
}

/**
 * Move transactions from one category to another.
 * @param {number} fromId - Source category ID
 * @param {number} toId - Target category ID
 * @returns {Promise<{moved: number}>}
 */
export function moveCategoryTransactions(fromId, toId) {
  return request('POST', `/categories/${fromId}/move-transactions?target_id=${toId}`)
}
