import { useState, useEffect, useCallback } from 'react'

/**
 * Hook for handling async data fetching with loading and error states.
 *
 * @param {Function} asyncFn - Async function to call
 * @param {Array} deps - Dependencies that trigger refetch
 * @param {Object} options - Options
 * @param {boolean} options.immediate - Whether to fetch immediately (default true)
 * @returns {Object} { data, loading, error, refetch }
 */
export function useAsync(asyncFn, deps = [], { immediate = true } = {}) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(immediate)
  const [error, setError] = useState(null)

  const execute = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const result = await asyncFn()
      setData(result)
      return result
    } catch (err) {
      setError(err)
      console.error(err)
      return null
    } finally {
      setLoading(false)
    }
  }, [asyncFn])

  useEffect(() => {
    if (immediate) {
      execute()
    }
  }, deps)

  return { data, loading, error, refetch: execute, setData }
}

/**
 * Simpler hook for one-time data fetch.
 *
 * @param {Function} asyncFn - Async function to call
 * @param {Array} deps - Dependencies
 * @returns {Object} { data, loading, error }
 */
export function useFetch(asyncFn, deps = []) {
  const [state, setState] = useState({
    data: null,
    loading: true,
    error: null,
  })

  useEffect(() => {
    let cancelled = false

    setState(prev => ({ ...prev, loading: true, error: null }))

    asyncFn()
      .then(data => {
        if (!cancelled) {
          setState({ data, loading: false, error: null })
        }
      })
      .catch(error => {
        if (!cancelled) {
          setState({ data: null, loading: false, error })
          console.error(error)
        }
      })

    return () => {
      cancelled = true
    }
  }, deps)

  return state
}

export default useAsync
