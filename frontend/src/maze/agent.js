/**
 * MAZE AGENT - Tool-based AI Solver
 * Uses OpenAI SDK with function calling for maze navigation
 */

import OpenAI from 'openai'

// ============================================
// ERROR TAXONOMY
// ============================================

export const ErrorTaxonomy = {
  // Authentication errors
  AUTH: {
    INVALID_API_KEY: 'AUTH_INVALID_API_KEY',
    MISSING_API_KEY: 'AUTH_MISSING_API_KEY',
    RATE_LIMITED: 'AUTH_RATE_LIMITED',
    INSUFFICIENT_CREDITS: 'AUTH_INSUFFICIENT_CREDITS'
  },
  
  // Network errors
  NETWORK: {
    CONNECTION_FAILED: 'NETWORK_CONNECTION_FAILED',
    TIMEOUT: 'NETWORK_TIMEOUT',
    REQUEST_FAILED: 'NETWORK_REQUEST_FAILED'
  },
  
  // Maze errors
  MAZE: {
    NO_PATH: 'MAZE_NO_PATH',
    START_BLOCKED: 'MAZE_START_BLOCKED',
    END_BLOCKED: 'MAZE_END_BLOCKED',
    INVALID_POSITION: 'MAZE_INVALID_POSITION',
    STUCK_IN_LOOP: 'MAZE_STUCK_IN_LOOP'
  },
  
  // Agent errors
  AGENT: {
    MAX_STEPS_REACHED: 'AGENT_MAX_STEPS_REACHED',
    INVALID_TOOL_CALL: 'AGENT_INVALID_TOOL_CALL',
    TOOL_EXECUTION_FAILED: 'AGENT_TOOL_EXECUTION_FAILED',
    PARSE_ERROR: 'AGENT_PARSE_ERROR',
    CONTEXT_OVERFLOW: 'AGENT_CONTEXT_OVERFLOW'
  },
  
  // Validation errors
  VALIDATION: {
    INVALID_RESPONSE: 'VALIDATION_INVALID_RESPONSE',
    SCHEMA_MISMATCH: 'VALIDATION_SCHEMA_MISMATCH'
  }
}

// ============================================
// LOG LEVELS
// ============================================

export const LogLevel = {
  DEBUG: 0,
  INFO: 1,
  WARN: 2,
  ERROR: 3
}

// ============================================
// STRUCTURED LOGGER
// ============================================

export class StructuredLogger {
  constructor(onLog) {
    this.logs = []
    this.onLog = onLog
    this.minLevel = LogLevel.INFO
  }

  log(level, category, code, message, data = {}) {
    const entry = {
      timestamp: new Date().toISOString(),
      level: Object.keys(LogLevel).find(k => LogLevel[k] === level) || 'INFO',
      category,
      code,
      message,
      data
    }
    
    this.logs.push(entry)
    this.onLog?.(entry)
    
    // Also log to browser console
    const consoleMsg = `[${entry.category}] ${entry.level}: ${entry.message}`
    switch (entry.level) {
      case 'DEBUG': console.debug(consoleMsg, data); break;
      case 'INFO': console.info(consoleMsg, data); break;
      case 'WARN': console.warn(consoleMsg, data); break;
      case 'ERROR': console.error(consoleMsg, data); break;
      default: console.log(consoleMsg, data);
    }
    
    return entry
  }

  debug(category, code, message, data) {
    return this.log(LogLevel.DEBUG, category, code, message, data)
  }

  info(category, code, message, data) {
    return this.log(LogLevel.INFO, category, code, message, data)
  }

  warn(category, code, message, data) {
    return this.log(LogLevel.WARN, category, code, message, data)
  }

  error(category, code, message, data) {
    return this.log(LogLevel.ERROR, category, code, message, data)
  }

  getLogs() {
    return [...this.logs]
  }

  clear() {
    this.logs = []
  }

  getErrorCount() {
    return this.logs.filter(l => l.level === 'ERROR').length
  }

  getWarnCount() {
    return this.logs.filter(l => l.level === 'WARN').length
  }
}

// ============================================
// MAZE AGENT
// ============================================

export class MazeAgent {
  constructor(maze, startCell, endCell) {
    this.maze = maze
    this.startCell = { ...startCell }
    this.endCell = { ...endCell }
    this.currentPosition = { ...startCell }
    this.path = [ { ...startCell } ]
    this.visited = new Set([`${startCell.x},${startCell.y}`])
    this.stepCount = 0
    this.maxSteps = maze.size * maze.size * 3
    this.isComplete = false
    this.controller = null
    
    this.logger = null
    this.onStep = null
    this.onToolCall = null
    this.onLog = null
  }

  setLogger(logger) {
    this.logger = logger
  }

  setCallbacks({ onStep, onToolCall, onLog }) {
    this.onStep = onStep
    this.onToolCall = onToolCall
    this.onLog = onLog
    if (onLog) {
      this.logger = new StructuredLogger(onLog)
    }
  }

  // Get visible maze from current position
  getMazeView(radius = 2) {
    const { x, y } = this.currentPosition
    const view = []
    
    for (let dy = -radius; dy <= radius; dy++) {
      for (let dx = -radius; dx <= radius; dx++) {
        const nx = x + dx
        const ny = y + dy
        
        if (nx >= 0 && nx < this.maze.size && ny >= 0 && ny < this.maze.size) {
          let cellType = 'empty'
          if (nx === this.endCell.x && ny === this.endCell.y) {
            cellType = 'end'
          } else if (nx === x && ny === y) {
            cellType = 'current'
          } else if (this.visited.has(`${nx},${ny}`)) {
            cellType = 'visited'
          }
          
          view.push({
            x: nx,
            y: ny,
            type: cellType,
            walls: this.maze.getCellWalls(nx, ny)
          })
        }
      }
    }
    
    return view
  }

  // Get full maze for initial context
  getFullMaze() {
    const cells = []
    for (let y = 0; y < this.maze.size; y++) {
      for (let x = 0; x < this.maze.size; x++) {
        let cellType = 'empty'
        if (x === this.startCell.x && y === this.startCell.y) {
          cellType = 'start'
        } else if (x === this.endCell.x && y === this.endCell.y) {
          cellType = 'end'
        }
        
        cells.push({
          x, y,
          type: cellType,
          walls: this.maze.getCellWalls(x, y)
        })
      }
    }
    return {
      size: this.maze.size,
      start: this.startCell,
      end: this.endCell,
      cells
    }
  }

  // Get ASCII visual representation of the maze
  getMazeVisual() {
    const size = this.maze.size
    let visual = ''
    
    // Top border
    visual += '┌' + '──┬' .repeat(size - 1) + '──┐\n'
    
    for (let y = 0; y < size; y++) {
      // Left wall
      let row = '│'
      
      for (let x = 0; x < size; x++) {
        const walls = this.maze.getCellWalls(x, y)
        
        // Cell content
        let cell = '  '
        if (x === this.startCell.x && y === this.startCell.y) {
          cell = 'S '
        } else if (x === this.endCell.x && y === this.endCell.y) {
          cell = 'E '
        }
        
        row += cell + (walls.right ? '│' : ' ')
      }
      visual += row + '\n'
      
      // Bottom walls (except for last row)
      if (y < size - 1) {
        let wallRow = ''
        for (let x = 0; x < size; x++) {
          const walls = this.maze.getCellWalls(x, y)
          wallRow += (walls.bottom ? '──┼' : '  ┼')
        }
        wallRow = wallRow.slice(0, -1) + '┤\n'
        visual += wallRow
      }
    }
    
    // Bottom border
    visual += '└' + '──┴' .repeat(size - 1) + '──┘'
    
    return visual
  }

  // Check if at end
  isAtEnd() {
    return this.currentPosition.x === this.endCell.x && 
           this.currentPosition.y === this.endCell.y
  }

  // Check if can move in direction
  canMove(direction) {
    const { x, y } = this.currentPosition
    const walls = this.maze.getCellWalls(x, y)
    
    switch (direction) {
      case 'up': return !walls.top
      case 'down': return !walls.bottom
      case 'left': return !walls.left
      case 'right': return !walls.right
      default: return false
    }
  }

  // Move in direction
  move(direction) {
    if (this.isComplete) {
      return {
        success: false,
        message: 'Already at end',
        position: this.currentPosition
      }
    }

    if (this.stepCount >= this.maxSteps) {
      this.logger?.error('AGENT', ErrorTaxonomy.AGENT.MAX_STEPS_REACHED, 
        'Maximum steps reached', { stepCount: this.stepCount })
      return {
        success: false,
        message: 'Maximum steps reached',
        position: this.currentPosition
      }
    }

    const canMove = this.canMove(direction)
    
    if (!canMove) {
      this.logger?.warn('AGENT', 'MOVEMENT_BLOCKED', 
        `Cannot move ${direction}, wall in the way`, { direction, position: this.currentPosition })
      return {
        success: false,
        message: `Cannot move ${direction}, wall in the way`,
        position: this.currentPosition
      }
    }

    // Calculate new position
    const newPos = { ...this.currentPosition }
    switch (direction) {
      case 'up': newPos.y--; break
      case 'down': newPos.y++; break
      case 'left': newPos.x--; break
      case 'right': newPos.x++; break
    }

    // Update position
    this.currentPosition = newPos
    this.path.push({ ...newPos })
    this.visited.add(`${newPos.x},${newPos.y}`)
    this.stepCount++

    // Check if complete
    if (this.isAtEnd()) {
      this.isComplete = true
      this.logger?.info('AGENT', 'MAZE_COMPLETE', 
        'Successfully solved the maze!', { 
          steps: this.stepCount, 
          pathLength: this.path.length 
        })
    }

    this.onStep?.({
      position: { ...this.currentPosition },
      direction,
      stepCount: this.stepCount,
      isComplete: this.isComplete,
      path: [...this.path]
    })

    return {
      success: true,
      message: `Moved ${direction} to (${newPos.x}, ${newPos.y})`,
      position: this.currentPosition,
      isComplete: this.isComplete,
      stepsTaken: this.stepCount
    }
  }

  // Get available moves
  getAvailableMoves() {
    return ['up', 'down', 'left', 'right'].filter(dir => this.canMove(dir))
  }

  // Check for loops
  detectLoop() {
    // Simple loop detection - if we've visited a cell more than once
    const positionCounts = {}
    for (const pos of this.path) {
      const key = `${pos.x},${pos.y}`
      positionCounts[key] = (positionCounts[key] || 0) + 1
      if (positionCounts[key] > 3) {
        return true
      }
    }
    return false
  }

  // Reset agent
  reset() {
    this.currentPosition = { ...this.startCell }
    this.path = [ { ...this.startCell } ]
    this.visited = new Set([`${this.startCell.x},${this.startCell.y}`])
    this.stepCount = 0
    this.isComplete = false
    this.logger?.clear()
  }

  cancel() {
    if (this.controller) {
      this.controller.abort()
    }
  }
}

// ============================================
// AGENT SOLVER - Uses OpenAI SDK with Tools
// ============================================

export class AgentSolver {
  constructor() {
    this.apiKey = ''
    this.model = 'openai/gpt-4o'
    this.controller = null
    this.agent = null
    this.messages = []
    this.isRunning = false
    this.logger = null
  }

  setApiKey(key) {
    this.apiKey = key
  }

  setModel(model) {
    this.model = model
  }

  setLogger(logger) {
    this.logger = logger
  }

  // Define tools for the AI to use
  getTools() {
    return [
      {
        type: 'function',
        function: {
          name: 'get_current_position',
          description: 'Get your current position in the maze and see surrounding cells',
          parameters: {
            type: 'object',
            properties: {},
            required: []
          }
        }
      },
      {
        type: 'function',
        function: {
          name: 'move_up',
          description: 'Move up in the maze (decreases Y coordinate)',
          parameters: {
            type: 'object',
            properties: {},
            required: []
          }
        }
      },
      {
        type: 'function',
        function: {
          name: 'move_down',
          description: 'Move down in the maze (increases Y coordinate)',
          parameters: {
            type: 'object',
            properties: {},
            required: []
          }
        }
      },
      {
        type: 'function',
        function: {
          name: 'move_left',
          description: 'Move left in the maze (decreases X coordinate)',
          parameters: {
            type: 'object',
            properties: {},
            required: []
          }
        }
      },
      {
        type: 'function',
        function: {
          name: 'move_right',
          description: 'Move right in the maze (increases X coordinate)',
          parameters: {
            type: 'object',
            properties: {},
            required: []
          }
        }
      },
      {
        type: 'function',
        function: {
          name: 'get_available_moves',
          description: 'Check which directions are available for movement from current position',
          parameters: {
            type: 'object',
            properties: {},
            required: []
          }
        }
      },
      {
        type: 'function',
        function: {
          name: 'check_goal',
          description: 'Check if you have reached the end/goal of the maze',
          parameters: {
            type: 'object',
            properties: {},
            required: []
          }
        }
      }
    ]
  }

  // Map tool names to agent methods
  executeTool(toolName) {
    switch (toolName) {
      case 'get_current_position':
        return {
          position: this.agent.currentPosition,
          view: this.agent.getMazeView(3),
          path: this.agent.path,
          visited: Array.from(this.agent.visited)
        }
      
      case 'move_up':
        return this.agent.move('up')
      
      case 'move_down':
        return this.agent.move('down')
      
      case 'move_left':
        return this.agent.move('left')
      
      case 'move_right':
        return this.agent.move('right')
      
      case 'get_available_moves':
        return {
          available: this.agent.getAvailableMoves(),
          position: this.agent.currentPosition
        }
      
      case 'check_goal':
        return {
          isComplete: this.agent.isComplete,
          position: this.agent.currentPosition,
          endPosition: this.agent.endCell,
          stepsTaken: this.agent.stepCount
        }
      
      default:
        throw new Error(`Unknown tool: ${toolName}`)
    }
  }

  // Main solve method with real-time updates
  async solve(maze, startCell, endCell, onProgress, onStep, onToolCall, onLog) {
    if (!this.apiKey) {
      throw new Error('OpenRouter API key is required')
    }

    this.controller = new AbortController()
    this.isRunning = true

    // Create agent
    this.agent = new MazeAgent(maze, startCell, endCell)
    
    // Setup logging
    const logger = new StructuredLogger(onLog)
    this.agent.setLogger(logger)
    this.agent.setCallbacks({ onStep, onToolCall })
    this.logger = logger

    logger.info('SOLVER', 'INIT_START', 'Starting agent solver', {
      mazeSize: maze.size,
      start: startCell,
      end: endCell
    })

    try {
      // Initialize OpenAI client
      const client = new OpenAI({
        apiKey: this.apiKey,
        baseURL: 'https://openrouter.ai/api/v1',
        defaultHeaders: {
          'HTTP-Referer': window.location?.href || 'http://localhost',
          'X-Title': 'Inception Maze Architect'
        },
        timeout: 120000,
        maxRetries: 2
      })

      // Initial system message with maze info
      const mazeInfo = this.agent.getFullMaze()
      const mazeVisual = this.agent.getMazeVisual()
      
      this.messages = [
        {
          role: 'system',
          content: `You are a maze-solving agent. You must navigate from START to END using the available tools.

MAZE INFORMATION:
- Grid size: ${mazeInfo.size}x${mazeInfo.size}
- Start position: (${startCell.x}, ${startCell.y})
- End position: (${endCell.x}, ${endCell.y})

MAZE MAP (S=Start, E=End, .=open, #=wall):
${mazeVisual}

WALL DATA (for each cell x,y: walls around it [top, right, bottom, left], 1=wall, 0=open):
${mazeInfo.cells.map(c => `(${c.x},${c.y}): [${c.walls.top?1:0},${c.walls.right?1:0},${c.walls.bottom?1:0},${c.walls.left?1:0}]`).join(' ')}

YOUR GOAL: Reach the END position at (${endCell.x}, ${endCell.y})

AVAILABLE TOOLS:
1. get_current_position - See where you are and the maze around you  
2. move_up, move_down, move_left, move_right - Move in a direction
3. get_available_moves - Check which directions are open from current position
4. check_goal - Check if you've reached the end

STRATEGY:
1. First, call get_current_position to see your surroundings
2. Use the maze map above to plan your optimal path
3. Use move tools to navigate step by step
4. After each move, verify with get_available_moves
5. Call check_goal when you think you might be at the end

IMPORTANT:
- You have the FULL maze information above - use it to plan!
- Move one step at a time
- Always check if your move was successful
- If you hit a wall, use a different direction
- The goal is at (${endCell.x}, ${endCell.y})

After reaching the end, explain your solution path.`
        },
        {
          role: 'user',
          content: `Start solving the maze! You're at (${startCell.x}, ${startCell.y}) and need to reach (${endCell.x}, ${endCell.y}). Begin by exploring your surroundings.`
        }
      ]

      onProgress?.('Initializing agent...', 5)

      let maxIterations = maze.size * maze.size * 2
      let iteration = 0
      let lastToolResult = null

      while (this.isRunning && iteration < maxIterations) {
        iteration++

        logger.debug('SOLVER', 'ITERATION', `Starting iteration ${iteration}`, {
          position: this.agent.currentPosition,
          isComplete: this.agent.isComplete
        })

        onProgress?.('AI is thinking...', 30 + Math.min(50, iteration))

        // Make the API call
        const response = await client.chat.completions.create({
          model: this.model,
          messages: this.messages,
          tools: this.getTools(),
          tool_choice: 'auto',
          temperature: 0.3,
          max_tokens: 2000
        })

        const assistantMessage = response.choices[0].message
        
        // Handle tool calls
        if (assistantMessage.tool_calls && assistantMessage.tool_calls.length > 0) {
          for (const toolCall of assistantMessage.tool_calls) {
            const toolName = toolCall.function.name
            
            logger.info('TOOL', 'CALL', `Executing tool: ${toolName}`, {
              toolCallId: toolCall.id,
              position: this.agent.currentPosition
            })

            onToolCall?.({
              toolName,
              toolCallId: toolCall.id,
              position: { ...this.agent.currentPosition },
              stepCount: this.agent.stepCount
            })

            // Execute tool
            let toolResult
            try {
              toolResult = this.executeTool(toolName)
            } catch (error) {
              logger.error('TOOL', 'EXECUTION_FAILED', 
                `Tool execution failed: ${error.message}`, { toolName, error: error.message })
              toolResult = { error: error.message }
            }

            lastToolResult = toolResult
            
            // Add messages
            this.messages.push({
              role: 'assistant',
              content: assistantMessage.content,
              tool_calls: [{
                id: toolCall.id,
                type: 'function',
                function: {
                  name: toolName,
                  arguments: toolCall.function.arguments
                }
              }]
            })

            this.messages.push({
              role: 'tool',
              tool_call_id: toolCall.id,
              content: JSON.stringify(toolResult)
            })

            // Check if complete
            if (toolName.startsWith('move_') && toolResult.isComplete) {
              logger.info('SOLVER', 'MAZE_SOLVED', 
                'Maze solved!', { 
                  steps: toolResult.stepsTaken,
                  pathLength: this.agent.path.length
                })
              onProgress?.('Complete!', 100)
              return {
                success: true,
                path: this.agent.path,
                steps: toolResult.stepsTaken,
                logs: logger.getLogs()
              }
            }

            // Check for stuck
            if (this.agent.detectLoop()) {
              logger.warn('AGENT', 'LOOP_DETECTED', 
                'Agent appears to be stuck in a loop', {
                  position: this.agent.currentPosition,
                  pathLength: this.agent.path.length
                })
            }
          }
        } else {
          // No tool call, just a text response
          this.messages.push({
            role: 'assistant',
            content: assistantMessage.content
          })
          
          // Check if the agent is done
          if (assistantMessage.content?.toLowerCase().includes('solved') || 
              assistantMessage.content?.toLowerCase().includes('complete')) {
            logger.info('SOLVER', 'COMPLETE', 'Agent reports maze complete')
            break
          }
        }

        // Check max steps
        if (this.agent.stepCount >= this.agent.maxSteps) {
          logger.error('AGENT', 'MAX_STEPS', 'Maximum iterations reached')
          break
        }

        // Small delay for visual feedback
        await new Promise(resolve => setTimeout(resolve, 100))
      }

      // Return what we have
      return {
        success: this.agent.isComplete,
        path: this.agent.path,
        steps: this.agent.stepCount,
        logs: logger.getLogs(),
        error: this.agent.isComplete ? null : 'Could not complete within step limit'
      }

    } catch (error) {
      logger.error('SOLVER', 'EXECUTION_ERROR', 
        `Solver error: ${error.message}`, { error: error.message })
      
      throw error
    } finally {
      this.isRunning = false
    }
  }

  cancel() {
    this.isRunning = false
    this.controller?.abort()
  }
}
