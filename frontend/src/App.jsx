import { Routes, Route, NavLink, useSearchParams } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { api, getMonthOptions } from './api'
import Dashboard from './pages/Dashboard'
import Transactions from './pages/Transactions'
import AddTransaction from './pages/AddTransaction'
import Budgets from './pages/Budgets'
import Import from './pages/Import'
import Rules from './pages/Rules'
import Accounts from './pages/Accounts'
import Categories from './pages/Categories'

const navItems = [
  { path: '/', label: 'Dashboard', icon: '📊' },
  { path: '/add', label: 'Add Transaction', icon: '➕' },
  { path: '/transactions', label: 'Transactions', icon: '📜' },
  { path: '/budgets', label: 'Budgets', icon: '💰' },
  { path: '/categories', label: 'Categories', icon: '🏷️' },
  { path: '/import', label: 'Import', icon: '📥' },
  { path: '/rules', label: 'Rules', icon: '📋' },
  { path: '/accounts', label: 'Accounts', icon: '🏦' },
]

export default function App() {
  const [searchParams, setSearchParams] = useSearchParams()
  const monthOptions = getMonthOptions()
  const [categories, setCategories] = useState([])
  const [accounts, setAccounts] = useState([])

  // Get month directly from URL (reactive to changes)
  const month = searchParams.get('month') || monthOptions[0]

  // Set initial month if not in URL
  useEffect(() => {
    if (!searchParams.get('month')) {
      setSearchParams({ month: monthOptions[0] }, { replace: true })
    }
  }, [])

  useEffect(() => {
    api.getCategories().then(setCategories).catch(console.error)
    api.getAccounts().then(data => setAccounts(data.accounts)).catch(console.error)
  }, [])

  const handleMonthChange = (newMonth) => {
    const params = new URLSearchParams(searchParams)
    params.set('month', newMonth)
    setSearchParams(params)
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      <aside className="w-64 bg-white border-r border-gray-200 p-4 flex flex-col">
        <h1 className="text-xl font-bold mb-6 text-gray-800">💰 Money Manager</h1>
        <select value={month} onChange={(e) => handleMonthChange(e.target.value)}
          className="mb-6 p-2 border rounded-lg bg-white text-sm">
          {monthOptions.map(m => <option key={m} value={m}>{m}</option>)}
        </select>
        <nav className="flex-1">
          {navItems.map(({ path, label, icon }) => (
            <NavLink key={path} to={`${path}?month=${month}`}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg mb-1 transition-colors ${
                  isActive ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-600 hover:bg-gray-100'
                }`}>
              <span>{icon}</span><span>{label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="flex-1 p-6 overflow-auto">
        <Routes>
          <Route path="/" element={<Dashboard month={month} categories={categories} />} />
          <Route path="/add" element={<AddTransaction categories={categories} accounts={accounts} />} />
          <Route path="/transactions" element={<Transactions month={month} categories={categories} accounts={accounts} />} />
          <Route path="/budgets" element={<Budgets month={month} categories={categories} />} />
          <Route path="/import" element={<Import accounts={accounts} />} />
          <Route path="/rules" element={<Rules categories={categories} />} />
          <Route path="/categories" element={<Categories />} />
          <Route path="/accounts" element={<Accounts />} />
        </Routes>
      </main>
    </div>
  )
}
