import { useState, useEffect } from 'react'
import { api } from '../api'

export default function Import({ accounts }) {
  const [files, setFiles] = useState([])
  const [previews, setPreviews] = useState([])
  const [manualAccounts, setManualAccounts] = useState({}) // filename -> account_id
  const [useAi, setUseAi] = useState(true)
  const [autoDetect, setAutoDetect] = useState(true)
  const [aiAvail, setAiAvail] = useState(false)
  const [importing, setImporting] = useState(false)
  const [results, setResults] = useState(null)

  useEffect(() => { api.getAiStatus().then(d => setAiAvail(d.available)).catch(() => {}) }, [])

  const handleFiles = async e => {
    const selectedFiles = Array.from(e.target.files)
    if (!selectedFiles.length) return
    setFiles(selectedFiles)
    setResults(null)

    // Preview each file
    const newPreviews = []
    for (const file of selectedFiles) {
      try {
        const preview = await api.previewImport(file)
        newPreviews.push({ file, ...preview })
      } catch {
        newPreviews.push({ file, error: 'Failed to parse' })
      }
    }
    setPreviews(newPreviews)
  }

  const handleImport = async () => {
    if (!files.length) return
    setImporting(true)
    setResults(null)
    try {
      // Import files one by one with their assigned accounts
      const allResults = []
      for (const p of previews) {
        if (p.error) continue
        const accountId = p.detected_account_id || manualAccounts[p.file.name]
        if (!accountId) continue
        const result = await api.importFiles([p.file], accountId, useAi, false)
        allResults.push(result)
      }
      if (allResults.length === 1) {
        setResults(allResults[0])
      } else {
        setResults({
          files: allResults,
          total_imported: allResults.reduce((sum, r) => sum + (r.imported || 0), 0)
        })
      }
      setFiles([])
      setPreviews([])
      setManualAccounts({})
    } catch (e) {
      alert('Failed: ' + e.message)
    } finally {
      setImporting(false)
    }
  }

  const setAccountSuffix = async (accountId, suffix) => {
    await api.updateAccount(accountId, { account_suffix: suffix })
    // Refresh previews
    const newPreviews = []
    for (const file of files) {
      try {
        const preview = await api.previewImport(file)
        newPreviews.push({ file, ...preview })
      } catch {
        newPreviews.push({ file, error: 'Failed to parse' })
      }
    }
    setPreviews(newPreviews)
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Import Bank Statements</h1>
      <p className="text-gray-500 mb-6">CSV/Excel files from Chase or Bank of America. Select multiple files at once.</p>

      {/* Results */}
      {results && (
        <div className="bg-green-50 text-green-700 p-4 rounded-lg mb-6">
          {results.files ? (
            <div>
              <div className="font-bold mb-2">Imported {results.total_imported} transactions from {results.files.length} files</div>
              {results.files.map((r, i) => (
                <div key={i} className="text-sm ml-4">
                  {r.filename}: {r.error ? <span className="text-red-600">{r.error}</span> : (
                    <>
                      {r.imported} imported to <b>{r.account_name}</b>
                      {r.auto_detected && <span className="text-blue-600"> (auto-detected)</span>}
                      {r.skipped > 0 && `, ${r.skipped} skipped`}
                    </>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div>
              Imported <b>{results.imported}</b> to <b>{results.account_name}</b>
              {results.auto_detected && <span className="text-blue-600"> (auto-detected)</span>}
              {results.rule_categorized > 0 && `, ${results.rule_categorized} by rules`}
              {results.ai_categorized > 0 && `, ${results.ai_categorized} by AI`}
              {results.skipped > 0 && `, ${results.skipped} skipped`}
            </div>
          )}
        </div>
      )}

      <div className="bg-white p-6 rounded-xl shadow-sm border max-w-2xl">
        {/* File Input */}
        <div className="mb-4">
          <label className="block text-sm mb-1">Files</label>
          <input type="file" accept=".csv,.xlsx" multiple onChange={handleFiles} className="w-full p-2 border rounded-lg"/>
        </div>

        {/* Options */}
        <div className="flex gap-6 mb-6">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={autoDetect} onChange={e => setAutoDetect(e.target.checked)} className="rounded"/>
            <span className="text-sm">Auto-detect account</span>
          </label>
          {aiAvail ? (
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={useAi} onChange={e => setUseAi(e.target.checked)} className="rounded"/>
              <span className="text-sm">Use AI (Ollama)</span>
            </label>
          ) : (
            <span className="text-sm text-gray-400">Ollama not available</span>
          )}
        </div>

        {/* Previews */}
        {previews.length > 0 && (
          <div className="mb-6 space-y-4">
            {previews.map((p, i) => (
              <div key={i} className="border rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">{p.file.name}</span>
                  <span className="text-sm text-gray-500">{p.format} - {p.count} transactions</span>
                </div>

                {p.error ? (
                  <div className="text-red-600 text-sm">{p.error}</div>
                ) : (
                  <>
                    {/* Detected Account */}
                    <div className="mb-2 text-sm">
                      {p.detected_account_name ? (
                        <span className="text-green-600">Account: <b>{p.detected_account_name}</b></span>
                      ) : (
                        <span className="text-orange-600">
                          Could not detect account. Select below:
                        </span>
                      )}
                    </div>

                    {/* Manual Account Selection (if not detected) */}
                    {!p.detected_account_name && (
                      <div className="mb-2">
                        <select
                          value={manualAccounts[p.file.name] || ''}
                          onChange={e => setManualAccounts(prev => ({ ...prev, [p.file.name]: parseInt(e.target.value) || null }))}
                          className="p-1 border rounded text-sm"
                        >
                          <option value="">Select account...</option>
                          {accounts.map(acc => (
                            <option key={acc.id} value={acc.id}>{acc.name}</option>
                          ))}
                        </select>
                      </div>
                    )}

                    {/* Transaction Preview */}
                    <div className="max-h-32 overflow-auto border rounded text-xs">
                      <table className="w-full">
                        <thead className="bg-gray-50 sticky top-0">
                          <tr>
                            <th className="p-1 text-left">Date</th>
                            <th className="p-1 text-left">Type</th>
                            <th className="p-1 text-left">Description</th>
                            <th className="p-1 text-right">Amount</th>
                          </tr>
                        </thead>
                        <tbody>
                          {p.transactions.slice(0, 10).map((t, j) => (
                            <tr key={j} className="border-t">
                              <td className="p-1">{t.date}</td>
                              <td className="p-1">
                                <span className={`px-1 rounded ${
                                  t.kind === 'transfer' ? 'bg-blue-100 text-blue-700' :
                                  t.kind === 'expense' ? 'bg-red-100 text-red-700' :
                                  'bg-green-100 text-green-700'
                                }`}>{t.kind}</span>
                              </td>
                              <td className="p-1 truncate max-w-[200px]">{t.description}</td>
                              <td className="p-1 text-right">${t.amount.toFixed(2)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        )}

        <button
          onClick={handleImport}
          disabled={!files.length || importing || previews.some(p => !p.error && !p.detected_account_id && !manualAccounts[p.file.name])}
          className="w-full py-2 bg-blue-600 text-white rounded-lg disabled:opacity-50"
        >
          {importing ? 'Importing...' : `Import ${files.length} file${files.length !== 1 ? 's' : ''}`}
        </button>

        {previews.some(p => !p.error && !p.detected_account_id && !manualAccounts[p.file.name]) && (
          <p className="text-orange-600 text-sm mt-2">Select an account for each file to enable import</p>
        )}
      </div>
    </div>
  )
}
