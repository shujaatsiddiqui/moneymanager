import { useSearchParams } from 'react-router-dom'
import { useEffect, useCallback } from 'react'
import { getMonthOptions, changeMonth as changeMonthUtil, getCurrentMonth } from '../utils'

/**
 * Hook for managing month from URL search params.
 *
 * @param {number} optionCount - Number of month options to generate
 * @returns {Object} { month, setMonth, changeMonth, monthOptions }
 */
export function useMonth(optionCount = 18) {
  const [searchParams, setSearchParams] = useSearchParams()
  const monthOptions = getMonthOptions(optionCount)
  const defaultMonth = monthOptions[0]

  // Get month from URL or use default
  const month = searchParams.get('month') || defaultMonth

  // Set initial month if not in URL
  useEffect(() => {
    if (!searchParams.get('month')) {
      setSearchParams({ month: defaultMonth }, { replace: true })
    }
  }, [])

  // Set month (updates URL)
  const setMonth = useCallback((newMonth) => {
    const params = new URLSearchParams(searchParams)
    params.set('month', newMonth)
    setSearchParams(params)
  }, [searchParams, setSearchParams])

  // Navigate prev/next month
  const changeMonth = useCallback((direction) => {
    const newMonth = changeMonthUtil(month, direction)
    setMonth(newMonth)
  }, [month, setMonth])

  return {
    month,
    setMonth,
    changeMonth,
    monthOptions,
  }
}

export default useMonth
