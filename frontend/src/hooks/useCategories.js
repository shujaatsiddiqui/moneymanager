import { useState, useEffect, useMemo } from 'react'
import { getCategories } from '../api'
import { flattenCategories } from '../utils'

/**
 * Hook for loading and managing categories.
 *
 * @returns {Object} { categories, flatCategories, loading, error, refetch }
 */
export function useCategories() {
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchCategories = async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await getCategories()
      setCategories(data)
    } catch (err) {
      setError(err)
      console.error('Failed to load categories:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCategories()
  }, [])

  // Memoized flat categories for dropdowns
  const flatCategories = useMemo(() => {
    return flattenCategories(categories)
  }, [categories])

  return {
    categories,
    flatCategories,
    loading,
    error,
    refetch: fetchCategories,
  }
}

export default useCategories
