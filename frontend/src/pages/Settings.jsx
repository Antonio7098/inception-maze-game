import { useEffect, useState } from 'react'
import { useAuth, SignOutButton } from '@clerk/clerk-react'
import { updateApiKey, getApiCalls, getStats } from '../api/backend'
import { setAuthToken } from '../api/backend'

export default function Settings() {
  const { getToken, user } = useAuth()
  const [apiKey, setApiKey] = useState('')
  const [saved, setSaved] = useState(false)
  const [activeTab, setActiveTab] = useState('api-key')
  const [period, setPeriod] = useState('all')
  const [apiCalls, setApiCalls] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getToken().then(token => {
      if (token) setAuthToken(token)
    })
  }, [getToken])

  useEffect(() => {
    if (activeTab === 'monitoring') {
      loadMonitoring()
    }
  }, [activeTab, period])

  const loadMonitoring = async () => {
    setLoading(true)
    try {
      const [callsData, statsData] = await Promise.all([
        getApiCalls(period),
        getStats()
      ])
      setApiCalls(callsData.calls || [])
      setStats(statsData)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleSaveApiKey = async () => {
    try {
      await updateApiKey(apiKey)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (err) {
      console.error(err)
      alert('Failed to save API key')
    }
  }

  const formatCost = (cost) => `$${(cost || 0).toFixed(6)}`

  return (
    <div className="page settings-page">
      <header className="page-header">
        <h1>Settings</h1>
        <p>Manage your account and API usage</p>
      </header>

      <div className="settings-tabs">
        <button className={activeTab === 'api-key' ? 'active' : ''} onClick={() => setActiveTab('api-key')}>API Key</button>
        <button className={activeTab === 'monitoring' ? 'active' : ''} onClick={() => setActiveTab('monitoring')}>Monitoring</button>
        <button className={activeTab === 'account' ? 'active' : ''} onClick={() => setActiveTab('account')}>Account</button>
      </div>

      <div className="settings-content">
        {activeTab === 'api-key' && (
          <div className="settings-section">
            <h2>OpenRouter API Key</h2>
            <p>Enter your OpenRouter API key to use paid models. Free models work without a key.</p>
            <div className="api-key-input">
              <input
                type="password"
                value={apiKey}
                onChange={e => setApiKey(e.target.value)}
                placeholder="sk-or-v1-..."
              />
              <button onClick={handleSaveApiKey} disabled={!apiKey}>
                {saved ? 'Saved!' : 'Save'}
              </button>
            </div>
            <p className="hint">Get your API key from <a href="https://openrouter.ai/keys" target="_blank" rel="noopener">openrouter.ai/keys</a></p>
          </div>
        )}

        {activeTab === 'monitoring' && (
          <div className="settings-section">
            <h2>API Usage</h2>
            
            <div className="period-filter">
              <button className={period === 'today' ? 'active' : ''} onClick={() => setPeriod('today')}>Today</button>
              <button className={period === 'week' ? 'active' : ''} onClick={() => setPeriod('week')}>Week</button>
              <button className={period === 'month' ? 'active' : ''} onClick={() => setPeriod('month')}>Month</button>
              <button className={period === 'all' ? 'active' : ''} onClick={() => setPeriod('all')}>All</button>
            </div>

            {stats && (
              <div className="stats-cards">
                <div className="stat-card">
                  <div className="stat-value">{stats.total_calls}</div>
                  <div className="stat-label">Total Calls</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{formatCost(stats.total_cost)}</div>
                  <div className="stat-label">Total Cost</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{stats.total_tokens?.toLocaleString()}</div>
                  <div className="stat-label">Total Tokens</div>
                </div>
              </div>
            )}

            {loading ? (
              <p>Loading...</p>
            ) : (
              <table className="api-calls-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Model</th>
                    <th>Tokens</th>
                    <th>Cost</th>
                    <th>Latency</th>
                  </tr>
                </thead>
                <tbody>
                  {apiCalls.map(call => (
                    <tr key={call.id}>
                      <td>{new Date(call.created_at).toLocaleString()}</td>
                      <td>{call.model.split('/').pop()}</td>
                      <td>{call.total_tokens?.toLocaleString()}</td>
                      <td>{formatCost(call.cost_usd)}</td>
                      <td>{call.latency_ms ? `${Math.round(call.latency_ms / 1000)}s` : '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {activeTab === 'account' && (
          <div className="settings-section">
            <h2>Account</h2>
            <div className="account-info">
              <p><strong>Email:</strong> {user?.primaryEmailAddress?.emailAddress || 'Not set'}</p>
              <p><strong>User ID:</strong> {user?.id}</p>
            </div>
            <SignOutButton>
              <button className="sign-out-btn">Sign Out</button>
            </SignOutButton>
          </div>
        )}
      </div>
    </div>
  )
}
