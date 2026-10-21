const API_BASE = '/api'

async function request(method, path, body = null) {
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

export const api = {
  getAccounts: () => request('GET', '/accounts'),
  getCategories: () => request('GET', '/categories'),
  createCategory: (data) => request('POST', '/categories', data),
  updateCategory: (id, data) => request('PATCH', `/categories/${id}`, data),
  deleteCategory: (id) => request('DELETE', `/categories/${id}`),
  deleteCategoryCascade: (id) => request('DELETE', `/categories/${id}/cascade`),
  getCategoryTransactions: (id) => request('GET', `/categories/${id}/transactions`),
  moveCategoryTransactions: (fromId, toId) => request('POST', `/categories/${fromId}/move-transactions?target_id=${toId}`),
  getBudgetStatus: (month) => request('GET', `/budgets/status?month=${month}`),
  setBudget: (data) => request('PUT', '/budgets', data),
  deleteBudget: (categoryId, month) =>
    request('DELETE', `/budgets?category_id=${categoryId}&month=${month}`),
  copyBudgets: (fromMonth, toMonth) =>
    request('POST', `/budgets/copy?from_month=${fromMonth}&to_month=${toMonth}`),
  getTransactions: (params = {}) => {
    const query = new URLSearchParams(params).toString()
    return request('GET', `/transactions?${query}`)
  },
  createTransaction: (data) => request('POST', '/transactions', data),
  updateTransaction: (id, data) => request('PATCH', `/transactions/${id}`, data),
  deleteTransaction: (id) => request('DELETE', `/transactions/${id}`),
  getRules: () => request('GET', '/rules'),
  createRule: (data) => request('POST', '/rules', data),
  deleteRule: (id) => request('DELETE', `/rules/${id}`),
  applyRules: () => request('POST', '/rules/apply'),
  suggestPattern: (description) => request('GET', `/rules/suggest-pattern?merchant=${encodeURIComponent(description)}`),
  getAiStatus: () => request('GET', '/import/ai-status'),
  importFiles: async (files, accountId, useAi, autoDetect = true) => {
    const formData = new FormData()
    files.forEach(file => formData.append('files', file))
    if (accountId) formData.append('account_id', accountId)
    formData.append('use_ai', useAi)
    formData.append('auto_detect_account', autoDetect)
    const res = await fetch(`${API_BASE}/import`, { method: 'POST', body: formData })
    if (!res.ok) throw new Error('Import failed')
    return res.json()
  },
  updateAccount: (id, data) => request('PATCH', `/accounts/${id}`, data),
  previewImport: async (file) => {
    const formData = new FormData()
    formData.append('file', file)
    const res = await fetch(`${API_BASE}/import/preview`, { method: 'POST', body: formData })
    if (!res.ok) throw new Error('Preview failed')
    return res.json()
  },
}

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
