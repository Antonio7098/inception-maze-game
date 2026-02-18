import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getChallenges, getChallengeSolutions, getChallengesStats } from '../api/backend'

export default function Challenges() {
  const [challenges, setChallenges] = useState([])
  const [solutions, setSolutions] = useState({})
  const [stats, setStats] = useState({})
  const [loading, setLoading] = useState(true)
  const [expandedChallenge, setExpandedChallenge] = useState(null)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      getChallenges(),
      getChallengesStats()
    ])
      .then(([challengesData, statsData]) => {
        setChallenges(challengesData.challenges || [])
        setStats(statsData.stats || {})
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const loadSolutions = async (challengeId) => {
    if (solutions[challengeId]) {
      setExpandedChallenge(expandedChallenge === challengeId ? null : challengeId)
      return
    }
    
    try {
      const data = await getChallengeSolutions(challengeId)
      setSolutions(prev => ({ ...prev, [challengeId]: data.solutions || [] }))
      setExpandedChallenge(challengeId)
    } catch (err) {
      console.error('Failed to load solutions:', err)
    }
  }

  const getDifficultyStars = (level) => '★'.repeat(level) + '☆'.repeat(5 - level)

  const formatDuration = (ms) => {
    if (!ms) return '-'
    const seconds = Math.floor(ms / 1000)
    if (seconds < 60) return `${seconds}s`
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}m ${remainingSeconds}s`
  }

  const getMedalEmoji = (medal) => {
    if (medal === 'gold') return '🥇'
    if (medal === 'silver') return '🥈'
    if (medal === 'bronze') return '🥉'
    return ''
  }

  if (loading) {
    return <div className="page-loading">Loading challenges...</div>
  }

  return (
    <div className="page challenges-page">
      <header className="page-header">
        <h1>Challenges</h1>
        <p>Create mazes that AI models solve in the target time</p>
      </header>

      <div className="challenges-info">
        <div className="info-card">
          <h4>Medal Thresholds</h4>
          <p>
            <span className="medal gold">🥇 Gold</span>: within ±10% of target time<br/>
            <span className="medal silver">🥈 Silver</span>: within ±15% of target time<br/>
            <span className="medal bronze">🥉 Bronze</span>: within ±20% of target time
          </p>
        </div>
      </div>

      <div className="challenges-grid">
        {challenges.map(challenge => {
          const challengeStats = stats[challenge.id] || {}
          const isExpanded = expandedChallenge === challenge.id
          const challengeSolutions = solutions[challenge.id] || []

          return (
            <div key={challenge.id} className="challenge-card-wrapper">
              <Link
                to={`/builder?challenge=${challenge.id}`}
                className="challenge-card"
              >
                <div className="challenge-difficulty">{getDifficultyStars(challenge.difficulty)}</div>
                <h3 className="challenge-name">{challenge.name}</h3>
                <p className="challenge-desc">{challenge.description}</p>
                <div className="challenge-meta">
                  <span className="challenge-model">{challenge.model.split('/').pop()}</span>
                  <span className="challenge-size">{challenge.grid_size}x{challenge.grid_size}</span>
                  <span className="challenge-time">{challenge.time_limit_minutes}min</span>
                </div>
                {challengeStats.total_solves > 0 && (
                  <div className="challenge-stats">
                    <span className="solves-count">{challengeStats.total_solves} solves</span>
                    {challengeStats.best_time_ms && (
                      <span className="best-time">Best: {formatDuration(challengeStats.best_time_ms)}</span>
                    )}
                  </div>
                )}
              </Link>
              
              {challengeStats.total_solves > 0 && (
                <button 
                  className="view-solutions-btn"
                  onClick={(e) => {
                    e.preventDefault()
                    loadSolutions(challenge.id)
                  }}
                >
                  {isExpanded ? '▲ Hide Solutions' : `▼ View Solutions (${challengeStats.total_solves})`}
                </button>
              )}
              
              {isExpanded && (
                <div className="solutions-panel">
                  {challengeSolutions.length === 0 ? (
                    <p className="no-solutions">No solutions yet</p>
                  ) : (
                    <table className="solutions-table">
                      <thead>
                        <tr>
                          <th>#</th>
                          <th>Model</th>
                          <th>User</th>
                          <th>Time</th>
                          <th>Steps</th>
                          <th>Medal</th>
                        </tr>
                      </thead>
                      <tbody>
                        {challengeSolutions.map((sol, idx) => (
                          <tr key={sol.attempt_id}>
                            <td>{idx + 1}</td>
                            <td className="model-name" title={sol.model}>
                              {sol.model.split('/').pop()}
                            </td>
                            <td>{sol.user_email}</td>
                            <td>{formatDuration(sol.duration_ms)}</td>
                            <td>{sol.steps}</td>
                            <td className="medal-cell">{getMedalEmoji(sol.medal)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
