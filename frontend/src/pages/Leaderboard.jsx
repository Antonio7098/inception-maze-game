import { useEffect, useState } from 'react'
import { getMazeBench } from '../api/backend'

export default function Leaderboard() {
  const [leaderboard, setLeaderboard] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    getMazeBench(100)
      .then(data => {
        setLeaderboard(data.leaderboard || [])
        setError(null)
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const getMedalIcon = (type) => {
    if (type === 'gold') return '🥇'
    if (type === 'silver') return '🥈'
    if (type === 'bronze') return '🥉'
    return ''
  }

  const formatModelName = (model) => {
    const parts = model.split('/')
    return parts.length > 1 ? parts[parts.length - 1] : model
  }

  const formatDuration = (ms) => {
    if (!ms) return '-'
    const seconds = Math.floor(ms / 1000)
    if (seconds < 60) return `${seconds}s`
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}m ${remainingSeconds}s`
  }

  if (loading) {
    return <div className="page-loading">Loading MazeBench leaderboard...</div>
  }

  if (error) {
    return <div className="page-error">Error: {error}</div>
  }

  return (
    <div className="page leaderboard-page">
      <header className="page-header">
        <h1>MazeBench Leaderboard</h1>
        <p>LLM performance across all mazes - ranked by normalized geometric mean score</p>
      </header>

      <div className="leaderboard-info">
        <div className="info-card">
          <h4>Scoring Method</h4>
          <p>
            Score = geometric mean of (median_time / model_time) across all mazes solved.
            Higher is better. Models must solve at least 1 maze to rank.
          </p>
        </div>
        <div className="info-card">
          <h4>Medal Thresholds</h4>
          <p>
            <span className="medal gold">🥇 Gold</span>: within 10% of best time<br/>
            <span className="medal silver">🥈 Silver</span>: within 15% of best time<br/>
            <span className="medal bronze">🥉 Bronze</span>: within 20% of best time
          </p>
        </div>
      </div>

      {leaderboard.length === 0 ? (
        <div className="empty-state">
          <p>No attempts recorded yet. Solve some mazes to see the leaderboard!</p>
        </div>
      ) : (
        <div className="leaderboard-table-container">
          <table className="leaderboard-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Model</th>
                <th>Score</th>
                <th>Solves</th>
                <th>Medals</th>
              </tr>
            </thead>
            <tbody>
              {leaderboard.map((entry, idx) => (
                <tr key={entry.model} className={idx < 3 ? `top-${idx + 1}` : ''}>
                  <td className="rank-cell">
                    {idx === 0 ? '🥇' : idx === 1 ? '🥈' : idx === 2 ? '🥉' : entry.rank}
                  </td>
                  <td className="model-cell">
                    <span className="model-name" title={entry.model}>
                      {formatModelName(entry.model)}
                    </span>
                  </td>
                  <td className="score-cell">
                    <span className="score-value">{entry.score.toFixed(4)}</span>
                  </td>
                  <td className="solves-cell">
                    <span className="successful">{entry.successful_solves}</span>
                    <span className="total">/{entry.total_solves}</span>
                  </td>
                  <td className="medals-cell">
                    {entry.gold_count > 0 && (
                      <span className="medal-count gold">{entry.gold_count}🥇</span>
                    )}
                    {entry.silver_count > 0 && (
                      <span className="medal-count silver">{entry.silver_count}🥈</span>
                    )}
                    {entry.bronze_count > 0 && (
                      <span className="medal-count bronze">{entry.bronze_count}🥉</span>
                    )}
                    {!entry.gold_count && !entry.silver_count && !entry.bronze_count && (
                      <span className="no-medals">-</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
