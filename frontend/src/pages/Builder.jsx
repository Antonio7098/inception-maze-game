import { useState, useRef, useEffect, useCallback } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { useAuth } from '@clerk/clerk-react'
import { Maze, CONFIG } from '../maze/mazeLogic'
import { getModels, createMaze, solveMaze, getChallenge } from '../api/backend'
import { setAuthToken } from '../api/backend'

export default function Builder() {
  const { getToken } = useAuth()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const challengeId = searchParams.get('challenge')
  
  const [currentTheme, setCurrentTheme] = useState('limbo')
  const [gridSize, setGridSize] = useState(15)
  const [maze, setMaze] = useState(null)
  const [startCell, setStartCell] = useState({ x: 0, y: 0 })
  const [endCell, setEndCell] = useState({ x: 14, y: 14 })
  const [cellSize, setCellSize] = useState(40)
  const [isDrawing, setIsDrawing] = useState(false)
  const [hoverDot, setHoverDot] = useState(null)
  
  const [models, setModels] = useState([])
  const [selectedModel, setSelectedModel] = useState('')
  const [isSolving, setIsSolving] = useState(false)
  const [agentPosition, setAgentPosition] = useState(null)
  const [agentStepCount, setAgentStepCount] = useState(0)
  const [aiPath, setAiPath] = useState([])
  const [logs, setLogs] = useState([])
  const [savedMazeId, setSavedMazeId] = useState(null)
  const [challenge, setChallenge] = useState(null)
  
  const canvasRef = useRef(null)
  const lastDotRef = useRef(null)
  const containerRef = useRef(null)
  const abortControllerRef = useRef(null)
  
  const colors = CONFIG.colors[currentTheme]

  useEffect(() => {
    getToken().then(token => {
      if (token) setAuthToken(token)
    })
  }, [getToken])

  useEffect(() => {
    getModels().then(data => {
      setModels(data.models || [])
      if (data.models?.length > 0) {
        setSelectedModel(data.models.find(m => m.is_free)?.id || data.models[0].id)
      }
    })
  }, [])

  useEffect(() => {
    if (challengeId) {
      getChallenge(challengeId).then(c => {
        setChallenge(c)
        setGridSize(c.grid_size)
        setSelectedModel(c.model)
        const newMaze = new Maze(c.grid_size)
        newMaze.generate()
        setMaze(newMaze)
        setEndCell({ x: c.grid_size - 1, y: c.grid_size - 1 })
      })
    }
  }, [challengeId])

  useEffect(() => {
    const updateSize = () => {
      if (!containerRef.current) return
      const container = containerRef.current
      const containerWidth = container.clientWidth - 32
      const containerHeight = container.clientHeight - 32
      const cellSizeByWidth = Math.floor(containerWidth / (gridSize + 1))
      const cellSizeByHeight = Math.floor(containerHeight / (gridSize + 1))
      setCellSize(Math.min(cellSizeByWidth, cellSizeByHeight, 50))
    }
    updateSize()
    window.addEventListener('resize', updateSize)
    return () => window.removeEventListener('resize', updateSize)
  }, [gridSize])

  useEffect(() => {
    if (!challengeId) setEndCell({ x: gridSize - 1, y: gridSize - 1 })
  }, [gridSize, challengeId])

  useEffect(() => {
    const canvas = canvasRef.current
    if (canvas) {
      const canvasSize = (gridSize + 1) * cellSize
      canvas.width = canvasSize
      canvas.height = canvasSize
    }
  }, [cellSize, gridSize])

  const getNearestDot = useCallback((clientX, clientY) => {
    const canvas = canvasRef.current
    if (!canvas) return null
    const padding = cellSize / 2
    const rect = canvas.getBoundingClientRect()
    const scaleX = canvas.width / rect.width
    const scaleY = canvas.height / rect.height
    const canvasX = (clientX - rect.left) * scaleX - padding
    const canvasY = (clientY - rect.top) * scaleY - padding
    const dotX = Math.round(canvasX / cellSize)
    const dotY = Math.round(canvasY / cellSize)
    if (dotX >= 0 && dotX <= gridSize && dotY >= 0 && dotY <= gridSize) {
      return { x: dotX, y: dotY }
    }
    return null
  }, [cellSize, gridSize])

  const drawCanvas = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const padding = cellSize / 2
    const isLight = currentTheme === 'snow'
    
    ctx.fillStyle = isLight ? '#e8eef2' : '#1a1a25'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    
    if (maze) {
      ctx.strokeStyle = colors.wall
      ctx.lineWidth = 3
      ctx.lineCap = 'round'
      ctx.beginPath()
      maze.walls.forEach(wallKey => {
        const [start, end] = wallKey.split('-')
        const [x1, y1] = start.split(',').map(Number)
        const [x2, y2] = end.split(',').map(Number)
        ctx.moveTo(x1 * cellSize + padding, y1 * cellSize + padding)
        ctx.lineTo(x2 * cellSize + padding, y2 * cellSize + padding)
      })
      ctx.stroke()
    }
    
    const dotRadius = Math.max(3, cellSize / 12)
    for (let y = 0; y <= gridSize; y++) {
      for (let x = 0; x <= gridSize; x++) {
        const px = x * cellSize + padding
        const py = y * cellSize + padding
        ctx.beginPath()
        ctx.arc(px, py, dotRadius, 0, Math.PI * 2)
        ctx.fillStyle = colors.grid + '80'
        ctx.fill()
      }
    }
    
    const sx = (startCell.x + 0.5) * cellSize + padding
    const sy = (startCell.y + 0.5) * cellSize + padding
    ctx.shadowColor = colors.start
    ctx.shadowBlur = 15
    ctx.fillStyle = colors.start
    ctx.beginPath()
    ctx.arc(sx, sy, cellSize / 3.5, 0, Math.PI * 2)
    ctx.fill()
    ctx.shadowBlur = 0
    ctx.fillStyle = '#fff'
    ctx.font = `bold ${Math.max(10, cellSize / 3.5)}px monospace`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText('S', sx, sy)
    
    const ex = (endCell.x + 0.5) * cellSize + padding
    const ey = (endCell.y + 0.5) * cellSize + padding
    ctx.shadowColor = colors.end
    ctx.shadowBlur = 15
    ctx.fillStyle = colors.end
    ctx.beginPath()
    ctx.arc(ex, ey, cellSize / 3.5, 0, Math.PI * 2)
    ctx.fill()
    ctx.shadowBlur = 0
    ctx.fillStyle = '#fff'
    ctx.fillText('E', ex, ey)
    
    if (agentPosition) {
      const ax = (agentPosition.x + 0.5) * cellSize + padding
      const ay = (agentPosition.y + 0.5) * cellSize + padding
      
      if (aiPath.length > 1) {
        ctx.strokeStyle = colors.ai
        ctx.lineWidth = 3
        ctx.beginPath()
        ctx.moveTo((aiPath[0].x + 0.5) * cellSize + padding, (aiPath[0].y + 0.5) * cellSize + padding)
        aiPath.forEach(p => ctx.lineTo((p.x + 0.5) * cellSize + padding, (p.y + 0.5) * cellSize + padding))
        ctx.stroke()
      }
      
      ctx.shadowColor = colors.ai
      ctx.shadowBlur = 20
      ctx.fillStyle = colors.ai
      ctx.beginPath()
      ctx.arc(ax, ay, cellSize / 3, 0, Math.PI * 2)
      ctx.fill()
      ctx.shadowBlur = 0
      ctx.fillText('🤖', ax, ay)
    }
  }, [maze, aiPath, currentTheme, cellSize, gridSize, startCell, endCell, agentPosition, colors])

  useEffect(() => {
    const animate = () => {
      drawCanvas()
      requestAnimationFrame(animate)
    }
    const id = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(id)
  }, [drawCanvas])

  const handleMouseDown = (e) => {
    if (isSolving) return
    const dot = getNearestDot(e.clientX, e.clientY)
    if (e.button === 2) {
      const cell = { x: Math.floor((e.clientX - canvasRef.current.getBoundingClientRect().left) / cellSize), y: Math.floor((e.clientY - canvasRef.current.getBoundingClientRect().top) / cellSize) }
      if (e.shiftKey) setEndCell(cell)
      else setStartCell(cell)
      return
    }
    if (dot) {
      setIsDrawing(true)
      lastDotRef.current = dot
    }
  }

  const handleMouseMove = (e) => {
    if (isSolving) return
    const dot = getNearestDot(e.clientX, e.clientY)
    setHoverDot(dot)
    if (!isDrawing || !lastDotRef.current) return
    
    if (dot && Math.abs(dot.x - lastDotRef.current.x) + Math.abs(dot.y - lastDotRef.current.y) === 1) {
      let newMaze = maze || new Maze(gridSize)
      newMaze.toggleWall(lastDotRef.current.x, lastDotRef.current.y, dot.x, dot.y)
      setMaze(newMaze)
      lastDotRef.current = dot
    }
  }

  const handleMouseUp = () => {
    setIsDrawing(false)
    lastDotRef.current = null
  }

  const generateMaze = () => {
    const newMaze = new Maze(gridSize)
    newMaze.generate()
    setMaze(newMaze)
    setAiPath([])
    setAgentPosition(null)
    setSavedMazeId(null)
  }

  const clearMaze = () => {
    setMaze(new Maze(gridSize))
    setAiPath([])
    setAgentPosition(null)
    setSavedMazeId(null)
  }

  const saveMaze = async () => {
    if (!maze) return
    const result = await createMaze({
      name: challenge?.name || `Maze ${gridSize}x${gridSize}`,
      size: gridSize,
      start: startCell,
      end: endCell,
      walls: Array.from(maze.walls)
    })
    setSavedMazeId(result.id)
  }

  const startSolving = async () => {
    if (!maze || isSolving) return
    
    let mazeId = savedMazeId
    if (!mazeId) {
      const result = await createMaze({
        name: challenge?.name || `Maze ${gridSize}x${gridSize}`,
        size: gridSize,
        start: startCell,
        end: endCell,
        walls: Array.from(maze.walls)
      })
      mazeId = result.id
      setSavedMazeId(mazeId)
    }
    
    abortControllerRef.current = new AbortController()
    setIsSolving(true)
    setAiPath([])
    setAgentPosition({ ...startCell })
    setAgentStepCount(0)
    setLogs([])
    
    try {
      await solveMaze(mazeId, selectedModel, (event) => {
        setLogs(prev => [...prev, { time: new Date().toISOString(), ...event }])
        if (event.event === 'position_update' && event.data?.position) {
          setAgentPosition(event.data.position)
          setAgentStepCount(event.data.step || 0)
          if (event.data.path) setAiPath(event.data.path)
        }
        if (event.event === 'complete') {
          setIsSolving(false)
        }
      }, abortControllerRef.current.signal)
    } catch (err) {
      if (err.name !== 'AbortError') console.error(err)
      setIsSolving(false)
    }
  }

  const cancelSolving = () => {
    abortControllerRef.current?.abort()
    setIsSolving(false)
  }

  return (
    <div className="page builder-page">
      <header className="page-header">
        <h1>{challenge ? challenge.name : 'Maze Builder'}</h1>
        {challenge && <p>{challenge.description}</p>}
      </header>

      <div className="builder-layout">
        <aside className="builder-sidebar">
          <div className="control-group">
            <label>Grid Size</label>
            <div className="size-buttons">
              {[10, 15, 20, 25].map(size => (
                <button key={size} className={gridSize === size ? 'active' : ''} onClick={() => !challengeId && setGridSize(size)}>{size}×{size}</button>
              ))}
            </div>
          </div>

          <div className="control-group">
            <label>Model</label>
            <select value={selectedModel} onChange={e => setSelectedModel(e.target.value)}>
              {models.map(m => (
                <option key={m.id} value={m.id}>{m.is_free ? '🆓 ' : ''}{m.name}</option>
              ))}
            </select>
          </div>

          <div className="control-group buttons">
            <button onClick={generateMaze}>Generate</button>
            <button onClick={clearMaze}>Clear</button>
            <button onClick={saveMaze} disabled={!maze}>Save</button>
          </div>

          <div className="control-group buttons">
            {!isSolving ? (
              <button className="primary" onClick={startSolving} disabled={!maze || !selectedModel}>Solve</button>
            ) : (
              <button className="danger" onClick={cancelSolving}>Cancel</button>
            )}
          </div>

          {agentStepCount > 0 && (
            <div className="stats">
              <div>Steps: {agentStepCount}</div>
            </div>
          )}
        </aside>

        <div className="canvas-container" ref={containerRef}>
          <canvas
            ref={canvasRef}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onContextMenu={e => e.preventDefault()}
          />
        </div>

        {logs.length > 0 && (
          <aside className="logs-sidebar">
            <h3>Logs</h3>
            <div className="logs-list">
              {logs.slice(-20).map((log, i) => (
                <div key={i} className="log-entry">
                  <span className="log-type">{log.event}</span>
                  <span className="log-data">{JSON.stringify(log.data || {}).slice(0, 50)}</span>
                </div>
              ))}
            </div>
          </aside>
        )}
      </div>
    </div>
  )
}
