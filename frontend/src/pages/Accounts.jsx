import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, formatMoney } from '../api'

export default function Accounts() {
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [suffixes, setSuffixes] = useState({})
  const [dueDays, setDueDays] = useState({})
  const [stmtDays, setStmtDays] = useState({})
  const [saving, setSaving] = useState(null)
  const [collapsed, setCollapsed] = useState({})

  const viewTransactions = (account) => {
    navigate(`/transactions?account=${account.id}&account_name=${encodeURIComponent(account.name)}`)
  }

  const loadData = async () => {
    const result = await api.getAccounts()
    setData(result)
    // Initialize local state
    const s = {}
    const d = {}
    const st = {}
    result.accounts.forEach(a => {
      s[a.id] = a.account_suffix || ''
      d[a.id] = a.due_day || ''
      st[a.id] = a.statement_day || ''
    })
    setSuffixes(s)
    setDueDays(d)
    setStmtDays(st)
    setLoading(false)
  }

  useEffect(() => { loadData() }, [])

  const handleSuffixChange = (id, value) => {
    setSuffixes(prev => ({ ...prev, [id]: value }))
  }

  const saveSuffix = async (id) => {
    const account = data.accounts.find(a => a.id === id)
    const original = account?.account_suffix || ''
    const newValue = suffixes[id] || ''

    if (newValue === original) return

    setSaving(id)
    try {
      await api.updateAccount(id, { account_suffix: newValue || null })
      await loadData()
    } catch (e) {
      alert('Failed to save: ' + e.message)
    }
    setSaving(null)
  }

  const handleDueDayChange = (id, value) => {
    // Only allow numbers 1-31 or empty
    const num = parseInt(value, 10)
    if (value === '' || (num >= 1 && num <= 31)) {
      setDueDays(prev => ({ ...prev, [id]: value }))
    }
  }

  const saveDueDay = async (id) => {
    const account = data.accounts.find(a => a.id === id)
    const original = account?.due_day || ''
    const newValue = dueDays[id] || ''

    if (String(newValue) === String(original)) return

    setSaving(id)
    try {
      await api.updateAccount(id, { due_day: newValue ? parseInt(newValue, 10) : null })
      await loadData()
    } catch (e) {
      alert('Failed to save: ' + e.message)
    }
    setSaving(null)
  }

  const handleStmtDayChange = (id, value) => {
    const num = parseInt(value, 10)
    if (value === '' || (num >= 1 && num <= 31)) {
      setStmtDays(prev => ({ ...prev, [id]: value }))
    }
  }

  const saveStmtDay = async (id) => {
    const account = data.accounts.find(a => a.id === id)
    const original = account?.statement_day || ''
    const newValue = stmtDays[id] || ''

    if (String(newValue) === String(original)) return

    setSaving(id)
    try {
      await api.updateAccount(id, { statement_day: newValue ? parseInt(newValue, 10) : null })
      await loadData()
    } catch (e) {
      alert('Failed to save: ' + e.message)
    }
    setSaving(null)
  }

  const toggleGroup = (group) => {
    setCollapsed(prev => ({ ...prev, [group]: !prev[group] }))
  }

  // Group accounts by their group field, splitting Card into Credit/Debit
  const groupedAccounts = data?.accounts?.reduce((acc, account) => {
    let group = account.group || 'Other'

    // Split Card group into Credit Card and Debit Card based on is_liability
    if (group === 'Card') {
      group = account.is_liability ? 'Credit Card' : 'Debit Card'
    }

    if (!acc[group]) acc[group] = []
    acc[group].push(account)
    return acc
  }, {}) || {}

  // Sort accounts within each group by balance
  // Credit cards: highest debt (most negative) first
  // Others: highest balance first
  Object.keys(groupedAccounts).forEach(group => {
    if (group === 'Credit Card') {
      // Sort by most negative first (largest debt on top)
      groupedAccounts[group].sort((a, b) => a.balance - b.balance)
    } else {
      // Sort by highest balance first
      groupedAccounts[group].sort((a, b) => b.balance - a.balance)
    }
  })

  // Calculate group totals
  const getGroupTotal = (accounts) => accounts.reduce((sum, a) => sum + a.balance, 0)

  // Define preferred group order
  const groupOrder = ['Credit Card', 'Debit Card', 'Accounts', 'Savings', 'Cash', 'Other']

  if (loading) return <div>Loading...</div>
  if (!data) return <div className="text-red-500">Failed to load</div>

  // Sort groups by preferred order, then alphabetically for any others
  const groups = Object.keys(groupedAccounts).sort((a, b) => {
    const aIndex = groupOrder.indexOf(a)
    const bIndex = groupOrder.indexOf(b)
    if (aIndex !== -1 && bIndex !== -1) return aIndex - bIndex
    if (aIndex !== -1) return -1
    if (bIndex !== -1) return 1
    return a.localeCompare(b)
  })

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Accounts</h1>
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="bg-white p-4 rounded-xl shadow-sm border"><div className="text-sm text-gray-500">Assets</div><div className="text-2xl font-bold text-green-600">{formatMoney(data.assets)}</div></div>
        <div className="bg-white p-4 rounded-xl shadow-sm border"><div className="text-sm text-gray-500">Liabilities</div><div className="text-2xl font-bold text-red-600">{formatMoney(data.liabilities)}</div></div>
        <div className="bg-white p-4 rounded-xl shadow-sm border"><div className="text-sm text-gray-500">Net Worth</div><div className={`text-2xl font-bold ${data.total >= 0 ? 'text-green-600' : 'text-red-600'}`}>{formatMoney(data.total)}</div></div>
      </div>

      <div className="space-y-4">
        {groups.map(group => {
          const accounts = groupedAccounts[group]
          const groupTotal = getGroupTotal(accounts)
          const isCollapsed = collapsed[group]

          return (
            <div key={group} className="bg-white rounded-xl shadow-sm border overflow-hidden">
              <button
                onClick={() => toggleGroup(group)}
                className="w-full flex items-center justify-between p-4 bg-gray-50 hover:bg-gray-100 transition-colors border-b"
              >
                <div className="flex items-center gap-3">
                  <span className={`transform transition-transform ${isCollapsed ? '' : 'rotate-90'}`}>
                    ▶
                  </span>
                  <span className="font-semibold text-lg">{group}</span>
                  <span className="text-sm text-gray-500">({accounts.length} accounts)</span>
                </div>
                <span className={`font-mono font-semibold ${groupTotal >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {formatMoney(groupTotal)}
                </span>
              </button>

              {!isCollapsed && (
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="text-left p-3">Account</th>
                      <th className="text-left p-3">Suffix (last 4)</th>
                      <th className="text-left p-3">Stmt Day</th>
                      <th className="text-left p-3">Due Day</th>
                      <th className="text-right p-3">Balance</th>
                      <th className="text-right p-3">Opening</th>
                      <th className="text-left p-3">Last Import</th>
                      <th className="text-center p-3">In Totals</th>
                      <th className="text-center p-3">Business</th>
                    </tr>
                  </thead>
                  <tbody>
                    {accounts.map(a => (
                      <tr key={a.id} className="border-b hover:bg-gray-50">
                        <td className="p-3 font-medium">
                          <button
                            onClick={() => viewTransactions(a)}
                            className="text-blue-600 hover:underline text-left"
                          >
                            {a.name}
                          </button>
                        </td>
                        <td className="p-3">
                          <input
                            type="text"
                            placeholder="e.g. 1234"
                            value={suffixes[a.id] || ''}
                            onChange={e => handleSuffixChange(a.id, e.target.value)}
                            onBlur={() => saveSuffix(a.id)}
                            onKeyDown={e => e.key === 'Enter' && saveSuffix(a.id)}
                            disabled={saving === a.id}
                            className={`w-20 px-2 py-1 border rounded text-sm ${saving === a.id ? 'opacity-50' : ''}`}
                          />
                          {saving === a.id && <span className="ml-1 text-xs text-gray-500">saving...</span>}
                        </td>
                        <td className="p-3">
                          {a.is_liability && a.group === 'Card' ? (
                            <input
                              type="text"
                              placeholder="1-31"
                              value={stmtDays[a.id] || ''}
                              onChange={e => handleStmtDayChange(a.id, e.target.value)}
                              onBlur={() => saveStmtDay(a.id)}
                              onKeyDown={e => e.key === 'Enter' && saveStmtDay(a.id)}
                              disabled={saving === a.id}
                              className={`w-14 px-2 py-1 border rounded text-sm text-center ${saving === a.id ? 'opacity-50' : ''}`}
                            />
                          ) : (
                            <span className="text-gray-300">—</span>
                          )}
                        </td>
                        <td className="p-3">
                          {a.is_liability && a.group === 'Card' ? (
                            <input
                              type="text"
                              placeholder="1-31"
                              value={dueDays[a.id] || ''}
                              onChange={e => handleDueDayChange(a.id, e.target.value)}
                              onBlur={() => saveDueDay(a.id)}
                              onKeyDown={e => e.key === 'Enter' && saveDueDay(a.id)}
                              disabled={saving === a.id}
                              className={`w-14 px-2 py-1 border rounded text-sm text-center ${saving === a.id ? 'opacity-50' : ''}`}
                            />
                          ) : (
                            <span className="text-gray-300">—</span>
                          )}
                        </td>
                        <td className={`p-3 text-right font-mono ${a.balance >= 0 ? 'text-green-600' : 'text-red-600'}`}>{formatMoney(a.balance)}</td>
                        <td className="p-3 text-right font-mono text-gray-500">{formatMoney(a.opening)}</td>
                        <td className="p-3 text-sm text-gray-500">
                          {a.last_tx_date ? (
                            <div>
                              <div>{a.last_tx_date}</div>
                              <div className="text-xs">{a.last_import_at ? new Date(a.last_import_at).toLocaleString() : ''}</div>
                            </div>
                          ) : '—'}
                        </td>
                        <td className="p-3 text-center">{a.include_in_totals ? '✓' : '—'}</td>
                        <td className="p-3 text-center">{a.is_business ? '✓' : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )
        })}
      </div>

      <p className="text-sm text-gray-500 mt-4">
        Type suffix and press Enter or click outside to save. Used for auto-detecting account during import.
        <br />
        Stmt Day: Day of month when statement is generated. Due Day: When payment is due. Both shown on Dashboard.
      </p>
    </div>
  )
}
