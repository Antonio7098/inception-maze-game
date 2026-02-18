import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '@clerk/clerk-react'
import { getMazes, getAttempts, getAttempt, deleteMaze } from '../api/backend'
import { setAuthToken } from '../api/backend'

export default function MyMazes() {
  const { getToken } = useAuth()
  const [mazes, setMazes] = useState([])
  const [selectedMaze, setSelectedMaze] = useState(null)
  const [attempts, setAttempts] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getToken().then(token => {
      if (token) setAuthToken(token)
    })
  }, [getToken])

  useEffect(() => {
    loadMazes()
  }, [])

  const loadMazes = async () => {
    try {
      const data = await getMazes()
      setMazes(data.mazes || [])
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const loadAttempts = async (mazeId) => {
    try {
      const data = await getAttempts(mazeId)
      setAttempts(data.attempts || [])
    } catch (err) {
      console.error(err)
    }
  }

  const handleSelectMaze = (maze) => {
    setSelectedMaze(maze)
    loadAttempts(maze.id)
  }

  const handleDeleteMaze = async (mazeId) => {
    if (confirm('Delete this maze?')) {
      await deleteMaze(mazeId)
      setMazes(mazes.filter(m => m.id !== mazeId))
      if (selectedMaze?.id === mazeId) setSelectedMaze(null)
    }
  }

  const formatDuration = (ms) => {
    if (!ms) return '-'
    const seconds = Math.floor(ms / 1000)
    return `${seconds}s`
  }

  const getMedalEmoji = (medal) => {
    if (medal === 'gold') return '🥇'
    if (medal === 'silver') return '🥈'
    if (medal === 'bronze') return '🥉'
    return ''
  }

  if (loading) {
    return <div className="page-loading">Loading mazes...</div>
  }

  return (
    <div className="page my-mazes-page">
      <header className="page-header">
        <h1>My Mazes</h1>
        <p>View your saved mazes and solve attempts</p>
      </header>

      <div className="mazes-layout">
        <aside className="mazes-list">
          {mazes.length === 0 ? (
            <div className="empty-state">
              <p>No saved mazes yet</p>
              <Link to="/builder">Create your first maze</Link>
            </div>
          ) : (
            mazes.map(maze => (
              <div
                key={maze.id}
                className={`maze-item ${selectedMaze?.id === maze.id ? 'active' : ''}`}
                onClick={() => handleSelectMaze(maze)}
              >
                <div className="maze-item-name">{maze.name}</div>
                <div className="maze-item-meta">{maze.size}x{maze.size}</div>
                <button
                  className="delete-btn"
                  onClick={(e) => { e.stopPropagation(); handleDeleteMaze(maze.id) }}
                >×</button>
              </div>
            ))
          )}
        </aside>

        <main className="mazes-detail">
          {selectedMaze ? (
            <>
              <h2>{selectedMaze.name}</h2>
              <div className="maze-info">
                <span>Size: {selectedMaze.size}x{selectedMaze.size}</span>
                <span>Start: ({selectedMaze.start.x}, {selectedMaze.start.y})</span>
                <span>End: ({selectedMaze.end.x}, {selectedMaze.end.y})</span>
              </div>

              <h3>Attempts ({attempts.length})</h3>
              {attempts.length === 0 ? (
                <p className="no-attempts">No attempts yet</p>
              ) : (
                <table className="attempts-table">
                  <thead>
                    <tr>
                      <th>Model</th>
                      <th>Success</th>
                      <th>Steps</th>
                      <th>Duration</th>
                      <th>Medal</th>
                      <th>Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {attempts.map(attempt => (
                      <tr key={attempt.id} className={attempt.success ? 'success' : 'failed'}>
                        <td>{attempt.model.split('/').pop()}</td>
                        <td>{attempt.success ? '✓' : '✗'}</td>
                        <td>{attempt.steps}</td>
                        <td>{formatDuration(attempt.duration_ms)}</td>
                        <td className="medal-cell">{getMedalEmoji(attempt.medal)}</td>
                        <td>{new Date(attempt.started_at).toLocaleDateString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}

              <Link to={`/builder?mazeId=${selectedMaze.id}`} className="edit-link">
                Edit Maze
              </Link>
            </>
          ) : (
            <div className="no-selection">
              <p>Select a maze to view details</p>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
