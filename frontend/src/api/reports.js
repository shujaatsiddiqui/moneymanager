import { request } from './client'

/**
 * Get Profit & Loss report for a month.
 * @param {string} month - Month in YYYY-MM format
 * @param {boolean|null} isBusiness - Filter by business (true), personal (false), or all (null)
 * @returns {Promise<Object>} P&L report with revenue, expenses, and summary
 */
export function getProfitLoss(month, isBusiness = null) {
  let url = `/reports/profit-loss?month=${month}`
  if (isBusiness !== null) {
    url += `&is_business=${isBusiness}`
  }
  return request('GET', url)
}

/**
 * Get Year-to-Date Profit & Loss report.
 * @param {number} year - Year for YTD report
 * @param {boolean|null} isBusiness - Filter by business (true), personal (false), or all (null)
 * @returns {Promise<Object>} YTD P&L report
 */
export function getYtdProfitLoss(year, isBusiness = null) {
  let url = `/reports/profit-loss/ytd?year=${year}`
  if (isBusiness !== null) {
    url += `&is_business=${isBusiness}`
  }
  return request('GET', url)
}
