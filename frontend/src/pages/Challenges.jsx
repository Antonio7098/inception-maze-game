import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getChallenges } from '../api/backend'

export default function Challenges() {
  const [challenges, setChallenges] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getChallenges()
      .then(data => setChallenges(data.challenges || []))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const getDifficultyStars = (level) => '★'.repeat(level) + '☆'.repeat(5 - level)

  if (loading) {
    return <div className="page-loading">Loading challenges...</div>
  }

  return (
    <div className="page challenges-page">
      <header className="page-header">
        <h1>Challenges</h1>
        <p>Create mazes that AI models can solve within the time limit</p>
      </header>

      <div className="challenges-grid">
        {challenges.map(challenge => (
          <Link
            key={challenge.id}
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
          </Link>
        ))}
      </div>
    </div>
  )
}
