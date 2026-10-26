import { useState, useEffect } from 'react'
import { getAccounts } from '../api'

/**
 * Hook for loading and managing accounts.
 *
 * @returns {Object} { accounts, summary, loading, error, refetch }
 */
export function useAccounts() {
  const [accounts, setAccounts] = useState([])
  const [summary, setSummary] = useState({ assets: 0, liabilities: 0, total: 0 })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchAccounts = async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await getAccounts()
      setAccounts(data.accounts || [])
      setSummary({
        assets: data.assets || 0,
        liabilities: data.liabilities || 0,
        total: data.total || 0,
      })
    } catch (err) {
      setError(err)
      console.error('Failed to load accounts:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAccounts()
  }, [])

  return {
    accounts,
    summary,
    loading,
    error,
    refetch: fetchAccounts,
  }
}

export default useAccounts
