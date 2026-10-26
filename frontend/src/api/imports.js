import { uploadRequest } from './client'
import { request } from './client'

/**
 * Check if AI categorization is available.
 * @returns {Promise<{available: boolean, model: string}>}
 */
export function getAiStatus() {
  return request('GET', '/import/ai-status')
}

/**
 * Import bank statement files.
 * @param {File[]} files - Files to import
 * @param {number|null} accountId - Target account ID (optional if auto-detect)
 * @param {boolean} useAi - Whether to use AI categorization
 * @param {boolean} autoDetect - Whether to auto-detect account
 * @returns {Promise<Object>}
 */
export async function importFiles(files, accountId, useAi, autoDetect = true) {
  const formData = new FormData()
  files.forEach(file => formData.append('files', file))
  if (accountId) formData.append('account_id', accountId)
  formData.append('use_ai', useAi)
  formData.append('auto_detect_account', autoDetect)

  return uploadRequest('/import', formData)
}

/**
 * Preview a file before importing.
 * @param {File} file - File to preview
 * @returns {Promise<Object>}
 */
export async function previewImport(file) {
  const formData = new FormData()
  formData.append('file', file)
  return uploadRequest('/import/preview', formData)
}

/**
 * Get import history.
 * @param {number} limit - Max number of records to return
 * @returns {Promise<Array>}
 */
export function getImportHistory(limit = 50) {
  return request('GET', `/import/history?limit=${limit}`)
}

/**
 * Revert an import batch (delete all its transactions).
 * @param {number} batchId - Import batch ID to revert
 * @returns {Promise<{batch_id: number, deleted_count: number}>}
 */
export function revertImport(batchId) {
  return request('DELETE', `/import/${batchId}`)
}
