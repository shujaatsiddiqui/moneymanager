import { useState, useCallback } from 'react'

/**
 * Hook for managing multi-selection state.
 *
 * @param {Array} items - Array of items with id property
 * @returns {Object} Selection state and handlers
 */
export function useSelection(items = []) {
  const [selectedIds, setSelectedIds] = useState(new Set())

  // Toggle single item selection
  const toggle = useCallback((id) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }, [])

  // Select all items
  const selectAll = useCallback(() => {
    setSelectedIds(new Set(items.map(item => item.id)))
  }, [items])

  // Clear all selections
  const clearAll = useCallback(() => {
    setSelectedIds(new Set())
  }, [])

  // Toggle all - if all selected, clear; otherwise select all
  const toggleAll = useCallback(() => {
    if (selectedIds.size === items.length) {
      clearAll()
    } else {
      selectAll()
    }
  }, [selectedIds.size, items.length, selectAll, clearAll])

  // Check if item is selected
  const isSelected = useCallback((id) => {
    return selectedIds.has(id)
  }, [selectedIds])

  // Get array of selected IDs
  const getSelectedIds = useCallback(() => {
    return Array.from(selectedIds)
  }, [selectedIds])

  // Get selected items
  const getSelectedItems = useCallback(() => {
    return items.filter(item => selectedIds.has(item.id))
  }, [items, selectedIds])

  return {
    selectedIds,
    selectedCount: selectedIds.size,
    allSelected: items.length > 0 && selectedIds.size === items.length,
    someSelected: selectedIds.size > 0 && selectedIds.size < items.length,
    toggle,
    selectAll,
    clearAll,
    toggleAll,
    isSelected,
    getSelectedIds,
    getSelectedItems,
  }
}

export default useSelection
