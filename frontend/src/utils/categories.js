/**
 * Flatten hierarchical categories into a flat array for dropdowns.
 * @param {Array} categories - Hierarchical category array
 * @returns {Array} Flat array with id and formatted name
 */
export function flattenCategories(categories) {
  const flat = []

  categories.forEach(cat => {
    flat.push({
      id: cat.id,
      name: `${cat.emoji || ''} ${cat.name}`.trim(),
      isParent: true,
    })

    if (cat.children) {
      cat.children.forEach(child => {
        flat.push({
          id: child.id,
          name: `  └ ${child.name}`,
          isParent: false,
          parentId: cat.id,
        })
      })
    }
  })

  return flat
}

/**
 * Get a category by ID from hierarchical categories.
 * @param {Array} categories - Hierarchical category array
 * @param {number} categoryId - Category ID to find
 * @returns {Object|null} Category object or null
 */
export function getCategoryById(categories, categoryId) {
  for (const cat of categories) {
    if (cat.id === categoryId) return cat
    if (cat.children) {
      const child = cat.children.find(c => c.id === categoryId)
      if (child) return { ...child, parent: cat }
    }
  }
  return null
}

/**
 * Get category display name (with parent if subcategory).
 * @param {Array} categories - Hierarchical category array
 * @param {number} categoryId - Category ID
 * @returns {string} Display name
 */
export function getCategoryDisplayName(categories, categoryId) {
  const cat = getCategoryById(categories, categoryId)
  if (!cat) return ''
  if (cat.parent) {
    return `${cat.parent.name} > ${cat.name}`
  }
  return cat.name
}
