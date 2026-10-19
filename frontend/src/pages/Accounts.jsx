import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, formatMoney } from '../api'

export default function Accounts() {
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [suffixes, setSuffixes] = useState({})
  const [saving, setSaving] = useState(null)

  const viewTransactions = (account) => {
    navigate(`/transactions?account=${account.id}&account_name=${encodeURIComponent(account.name)}`)
  }

  const loadData = async () => {
    const result = await api.getAccounts()
    setData(result)
    // Initialize local suffix state
    const s = {}
    result.accounts.forEach(a => { s[a.id] = a.account_suffix || '' })
    setSuffixes(s)
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

  if (loading) return <div>Loading...</div>
  if (!data) return <div className="text-red-500">Failed to load</div>

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Accounts</h1>
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="bg-white p-4 rounded-xl shadow-sm border"><div className="text-sm text-gray-500">Assets</div><div className="text-2xl font-bold text-green-600">{formatMoney(data.assets)}</div></div>
        <div className="bg-white p-4 rounded-xl shadow-sm border"><div className="text-sm text-gray-500">Liabilities</div><div className="text-2xl font-bold text-red-600">{formatMoney(data.liabilities)}</div></div>
        <div className="bg-white p-4 rounded-xl shadow-sm border"><div className="text-sm text-gray-500">Net Worth</div><div className={`text-2xl font-bold ${data.total >= 0 ? 'text-green-600' : 'text-red-600'}`}>{formatMoney(data.total)}</div></div>
      </div>
      <div className="bg-white rounded-xl shadow-sm border">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left p-3">Group</th>
              <th className="text-left p-3">Account</th>
              <th className="text-left p-3">Suffix (last 4)</th>
              <th className="text-right p-3">Balance</th>
              <th className="text-right p-3">Opening</th>
              <th className="text-center p-3">In Totals</th>
              <th className="text-center p-3">Business</th>
            </tr>
          </thead>
          <tbody>
            {data.accounts.map(a => (
              <tr key={a.id} className="border-b">
                <td className="p-3">{a.group}</td>
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
                <td className={`p-3 text-right font-mono ${a.balance >= 0 ? 'text-green-600' : 'text-red-600'}`}>{formatMoney(a.balance)}</td>
                <td className="p-3 text-right font-mono text-gray-500">{formatMoney(a.opening)}</td>
                <td className="p-3 text-center">{a.include_in_totals ? '✓' : '—'}</td>
                <td className="p-3 text-center">{a.is_business ? '✓' : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-sm text-gray-500 mt-4">
        Type suffix and press Enter or click outside to save. Used for auto-detecting account during import.
      </p>
    </div>
  )
}
