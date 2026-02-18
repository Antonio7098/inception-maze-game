const API_BASE = 'http://localhost:8000'

let authToken = null

export function setAuthToken(token) {
  authToken = token
}

export function clearAuthToken() {
  authToken = null
}

async function fetchAPI(endpoint, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  }
  
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`
  }
  
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  })
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(error.detail || 'Request failed')
  }
  
  return response.json()
}

export async function getModels() {
  return fetchAPI('/api/models')
}

export async function getChallenges() {
  return fetchAPI('/api/challenges')
}

export async function getChallenge(id) {
  return fetchAPI(`/api/challenges/${id}`)
}

export async function getMe() {
  return fetchAPI('/api/auth/me')
}

export async function updateApiKey(apiKey) {
  return fetchAPI('/api/auth/api-key', {
    method: 'POST',
    body: JSON.stringify({ api_key: apiKey }),
  })
}

export async function getMazes() {
  return fetchAPI('/api/mazes')
}

export async function createMaze(maze) {
  return fetchAPI('/api/mazes', {
    method: 'POST',
    body: JSON.stringify(maze),
  })
}

export async function getMaze(id) {
  return fetchAPI(`/api/mazes/${id}`)
}

export async function deleteMaze(id) {
  return fetchAPI(`/api/mazes/${id}`, { method: 'DELETE' })
}

export async function getAttempts(mazeId) {
  return fetchAPI(`/api/mazes/${mazeId}/attempts`)
}

export async function getAttempt(id) {
  return fetchAPI(`/api/attempts/${id}`)
}

export async function getApiCalls(period = 'all') {
  return fetchAPI(`/api/monitoring/api-calls?period=${period}`)
}

export async function getStats() {
  return fetchAPI('/api/monitoring/stats')
}

export async function solveMaze(mazeId, model, onEvent, signal) {
  const response = await fetch(`${API_BASE}/api/attempts`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${authToken}`,
    },
    body: JSON.stringify({ maze_id: mazeId, model }),
    signal,
  })
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(error.detail || 'Request failed')
  }
  
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    
    const chunk = decoder.decode(value)
    const lines = chunk.split('\n')
    
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6))
          onEvent(data)
        } catch (e) {
          // Ignore parse errors
        }
      }
    }
  }
}

export async function getMazeBench(limit = 50) {
  return fetchAPI(`/api/mazebench?limit=${limit}`)
}

export async function getChallengeSolutions(challengeId, limit = 50) {
  return fetchAPI(`/api/challenges/${challengeId}/solutions?limit=${limit}`)
}

export async function getChallengesStats() {
  return fetchAPI('/api/challenges/stats')
}

export async function getMazeStats(mazeId) {
  return fetchAPI(`/api/mazes/${mazeId}/stats`)
}
