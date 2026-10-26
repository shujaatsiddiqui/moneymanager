/**
 * API client for HTTP requests.
 */

const API_BASE = '/api'

/**
 * Make an HTTP request to the API.
 * @param {string} method - HTTP method
 * @param {string} path - API path (without base)
 * @param {Object|null} body - Request body (will be JSON stringified)
 * @returns {Promise<any>} Response data
 */
export async function request(method, path, body = null) {
  const options = {
    method,
    headers: { 'Content-Type': 'application/json' },
  }

  if (body) {
    options.body = JSON.stringify(body)
  }

  const res = await fetch(`${API_BASE}${path}`, options)

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(error.detail || 'Request failed')
  }

  return res.json()
}

/**
 * Make a FormData request (for file uploads).
 * @param {string} path - API path
 * @param {FormData} formData - Form data to send
 * @returns {Promise<any>} Response data
 */
export async function uploadRequest(path, formData) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    body: formData,
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(error.detail || 'Upload failed')
  }

  return res.json()
}

/**
 * Build query string from params object.
 * @param {Object} params - Query parameters
 * @returns {string} Query string
 */
export function buildQuery(params) {
  return new URLSearchParams(params).toString()
}
