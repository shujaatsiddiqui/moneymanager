import { useState, useEffect } from 'react'
import { api } from '../api'

export default function Categories() {
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(true)
  const [editingId, setEditingId] = useState(null)
  const [editForm, setEditForm] = useState({})
  const [newCategory, setNewCategory] = useState({ name: '', emoji: '', parent_id: null, exclude_from_budget: false })
  const [showNewForm, setShowNewForm] = useState(false)
  const [error, setError] = useState('')
  const [deleteModal, setDeleteModal] = useState(null) // { id, name, txnData, cascade, targetId }
  const [deleteLoading, setDeleteLoading] = useState(false)

  const loadCategories = async () => {
    setLoading(true)
    try {
      const data = await api.getCategories()
      setCategories(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadCategories() }, [])

  const handleCreate = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await api.createCategory({
        name: newCategory.name,
        emoji: newCategory.emoji || null,
        parent_id: newCategory.parent_id || null,
        exclude_from_budget: newCategory.exclude_from_budget,
      })
      setNewCategory({ name: '', emoji: '', parent_id: null, exclude_from_budget: false })
      setShowNewForm(false)
      loadCategories()
    } catch (e) {
      setError(e.message)
    }
  }

  const handleUpdate = async (id) => {
    setError('')
    try {
      await api.updateCategory(id, editForm)
      setEditingId(null)
      setEditForm({})
      loadCategories()
    } catch (e) {
      setError(e.message)
    }
  }

  // Check for transactions before deleting
  const initiateDelete = async (id, name, cascade = false) => {
    setError('')
    setDeleteLoading(true)
    try {
      const txnData = await api.getCategoryTransactions(id)
      const totalTxns = txnData.total_count || 0

      if (totalTxns > 0) {
        // Has transactions - show modal to move them first
        setDeleteModal({ id, name, txnData, cascade, targetId: '' })
      } else {
        // No transactions - confirm and delete directly
        if (confirm(`Delete category "${name}"${cascade ? ' and all subcategories' : ''}?`)) {
          if (cascade) {
            await api.deleteCategoryCascade(id)
          } else {
            await api.deleteCategory(id)
          }
          loadCategories()
        }
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setDeleteLoading(false)
    }
  }

  const handleMoveAndDelete = async () => {
    if (!deleteModal) return
    const { id, cascade, targetId } = deleteModal

    if (!targetId) {
      setError('Please select a category to move transactions to')
      return
    }

    setDeleteLoading(true)
    setError('')
    try {
      // Move transactions first
      await api.moveCategoryTransactions(id, parseInt(targetId))
      // Then delete the category
      if (cascade) {
        await api.deleteCategoryCascade(id)
      } else {
        await api.deleteCategory(id)
      }
      setDeleteModal(null)
      loadCategories()
    } catch (e) {
      setError(e.message)
    } finally {
      setDeleteLoading(false)
    }
  }

  // Build flat list of all categories for the target dropdown
  const getAllCategoryOptions = () => {
    const options = []
    categories.forEach(parent => {
      if (deleteModal && parent.id !== deleteModal.id) {
        options.push({ id: parent.id, name: `${parent.emoji || ''} ${parent.name}`.trim(), level: 0 })
      }
      parent.children?.forEach(child => {
        if (deleteModal && child.id !== deleteModal.id) {
          options.push({ id: child.id, name: `  └ ${child.name}`, level: 1 })
        }
      })
    })
    return options
  }

  const startEdit = (cat, isChild = false) => {
    setEditingId(cat.id)
    setEditForm({
      name: cat.name,
      emoji: cat.emoji || '',
      exclude_from_budget: cat.exclude_from_budget || false,
    })
  }

  if (loading) return <div className="text-gray-500">Loading...</div>

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Categories</h1>
        <button
          onClick={() => setShowNewForm(!showNewForm)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          {showNewForm ? 'Cancel' : '+ New Category'}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 p-3 rounded-lg mb-4">
          {error}
        </div>
      )}

      {/* Delete Modal */}
      {deleteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-md w-full mx-4 shadow-xl">
            <h3 className="text-lg font-bold mb-4">Move Transactions Before Delete</h3>
            <p className="text-gray-600 mb-4">
              <strong>{deleteModal.name}</strong> has transactions that need to be moved:
            </p>
            <div className="bg-gray-50 p-3 rounded-lg mb-4 text-sm">
              {deleteModal.txnData.categories?.map(cat => (
                <div key={cat.id} className="flex justify-between py-1">
                  <span>{cat.name}</span>
                  <span className="font-medium">{cat.count} transaction{cat.count !== 1 ? 's' : ''}</span>
                </div>
              ))}
              <div className="border-t mt-2 pt-2 flex justify-between font-medium">
                <span>Total</span>
                <span>{deleteModal.txnData.total_count} transaction{deleteModal.txnData.total_count !== 1 ? 's' : ''}</span>
              </div>
            </div>
            <div className="mb-4">
              <label className="block text-sm font-medium mb-1">Move all transactions to:</label>
              <select
                value={deleteModal.targetId}
                onChange={e => setDeleteModal({ ...deleteModal, targetId: e.target.value })}
                className="w-full p-2 border rounded-lg"
              >
                <option value="">-- Select category --</option>
                {getAllCategoryOptions().map(opt => (
                  <option key={opt.id} value={opt.id}>{opt.name}</option>
                ))}
              </select>
            </div>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setDeleteModal(null)}
                className="px-4 py-2 bg-gray-200 rounded-lg hover:bg-gray-300"
                disabled={deleteLoading}
              >
                Cancel
              </button>
              <button
                onClick={handleMoveAndDelete}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
                disabled={deleteLoading || !deleteModal.targetId}
              >
                {deleteLoading ? 'Processing...' : 'Move & Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* New Category Form */}
      {showNewForm && (
        <form onSubmit={handleCreate} className="bg-white p-4 rounded-xl shadow-sm border mb-6">
          <h2 className="font-medium mb-3">New Category</h2>
          <div className="grid grid-cols-4 gap-4">
            <div>
              <label className="block text-sm mb-1">Emoji</label>
              <input
                type="text"
                value={newCategory.emoji}
                onChange={e => setNewCategory({ ...newCategory, emoji: e.target.value })}
                placeholder="🏠"
                className="w-full p-2 border rounded-lg"
                maxLength={2}
              />
            </div>
            <div>
              <label className="block text-sm mb-1">Name</label>
              <input
                type="text"
                value={newCategory.name}
                onChange={e => setNewCategory({ ...newCategory, name: e.target.value })}
                placeholder="Category name"
                className="w-full p-2 border rounded-lg"
                required
              />
            </div>
            <div>
              <label className="block text-sm mb-1">Parent (optional)</label>
              <select
                value={newCategory.parent_id || ''}
                onChange={e => setNewCategory({ ...newCategory, parent_id: e.target.value ? parseInt(e.target.value) : null })}
                className="w-full p-2 border rounded-lg"
              >
                <option value="">None (top-level)</option>
                {categories.map(c => (
                  <option key={c.id} value={c.id}>{c.emoji} {c.name}</option>
                ))}
              </select>
            </div>
            <div className="flex items-end gap-2">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={newCategory.exclude_from_budget}
                  onChange={e => setNewCategory({ ...newCategory, exclude_from_budget: e.target.checked })}
                  className="rounded"
                />
                <span className="text-sm">Exclude from budget</span>
              </label>
              <button type="submit" className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">
                Create
              </button>
            </div>
          </div>
        </form>
      )}

      {/* Categories List */}
      <div className="bg-white rounded-xl shadow-sm border">
        {categories.length === 0 ? (
          <div className="p-4 text-gray-500">No categories yet.</div>
        ) : (
          categories.map(parent => (
            <div key={parent.id} className="border-b last:border-b-0">
              {/* Parent Category */}
              <div className="p-4 flex items-center justify-between hover:bg-gray-50">
                {editingId === parent.id ? (
                  <div className="flex items-center gap-2 flex-1">
                    <input
                      type="text"
                      value={editForm.emoji}
                      onChange={e => setEditForm({ ...editForm, emoji: e.target.value })}
                      className="w-12 p-1 border rounded text-center"
                      maxLength={2}
                    />
                    <input
                      type="text"
                      value={editForm.name}
                      onChange={e => setEditForm({ ...editForm, name: e.target.value })}
                      className="flex-1 p-1 border rounded"
                    />
                    <label className="flex items-center gap-1 text-sm">
                      <input
                        type="checkbox"
                        checked={editForm.exclude_from_budget}
                        onChange={e => setEditForm({ ...editForm, exclude_from_budget: e.target.checked })}
                        className="rounded"
                      />
                      Exclude
                    </label>
                    <button onClick={() => handleUpdate(parent.id)} className="px-2 py-1 bg-green-600 text-white rounded text-sm">Save</button>
                    <button onClick={() => setEditingId(null)} className="px-2 py-1 bg-gray-200 rounded text-sm">Cancel</button>
                  </div>
                ) : (
                  <>
                    <div className="flex items-center gap-2">
                      <span className="text-xl">{parent.emoji}</span>
                      <span className="font-medium">{parent.name}</span>
                      {parent.exclude_from_budget && (
                        <span className="text-xs bg-gray-200 px-2 py-0.5 rounded">excluded</span>
                      )}
                      <span className="text-gray-400 text-sm">({parent.children?.length || 0} subcategories)</span>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => startEdit(parent)}
                        className="px-2 py-1 text-blue-600 hover:bg-blue-50 rounded text-sm"
                      >
                        Edit
                      </button>
                      {parent.children?.length > 0 && (
                        <button
                          onClick={() => initiateDelete(parent.id, parent.name, true)}
                          className="px-2 py-1 text-orange-600 hover:bg-orange-50 rounded text-sm"
                          disabled={deleteLoading}
                        >
                          Delete All
                        </button>
                      )}
                      <button
                        onClick={() => initiateDelete(parent.id, parent.name, false)}
                        className="px-2 py-1 text-red-600 hover:bg-red-50 rounded text-sm"
                        disabled={deleteLoading}
                      >
                        Delete
                      </button>
                    </div>
                  </>
                )}
              </div>

              {/* Children */}
              {parent.children?.map(child => (
                <div key={child.id} className="p-3 pl-12 flex items-center justify-between hover:bg-gray-50 border-t border-gray-100">
                  {editingId === child.id ? (
                    <div className="flex items-center gap-2 flex-1">
                      <span className="text-gray-400">└</span>
                      <input
                        type="text"
                        value={editForm.name}
                        onChange={e => setEditForm({ ...editForm, name: e.target.value })}
                        className="flex-1 p-1 border rounded"
                      />
                      <button onClick={() => handleUpdate(child.id)} className="px-2 py-1 bg-green-600 text-white rounded text-sm">Save</button>
                      <button onClick={() => setEditingId(null)} className="px-2 py-1 bg-gray-200 rounded text-sm">Cancel</button>
                    </div>
                  ) : (
                    <>
                      <div className="flex items-center gap-2">
                        <span className="text-gray-400">└</span>
                        <span>{child.name}</span>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => startEdit(child, true)}
                          className="px-2 py-1 text-blue-600 hover:bg-blue-50 rounded text-sm"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => initiateDelete(child.id, child.name, false)}
                          className="px-2 py-1 text-red-600 hover:bg-red-50 rounded text-sm"
                          disabled={deleteLoading}
                        >
                          Delete
                        </button>
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          ))
        )}
      </div>
    </div>
  )
}
