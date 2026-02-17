/**
 * MAZE LOGIC - Dot Connection Model
 * Walls are created by connecting dots
 */

export const CONFIG = {
  themes: ['limbo', 'hotel', 'snow'],
  themeNames: {
    limbo: 'LIMBO',
    hotel: 'HOTEL',
    snow: 'SNOW FORTRESS'
  },
  colors: {
    limbo: {
      wall: '#6366f1',
      path: '#1a1a25',
      start: '#22c55e',
      end: '#ef4444',
      ai: '#a855f7',
      grid: '#2a2a35'
    },
    hotel: {
      wall: '#d4af37',
      path: '#1a1610',
      start: '#22c55e',
      end: '#ef4444',
      ai: '#e6c875',
      grid: '#2a2420'
    },
    snow: {
      wall: '#2c5282',
      path: '#e8eef2',
      start: '#22c55e',
      end: '#ef4444',
      ai: '#4a7ab8',
      grid: '#c0c9d0'
    }
  }
};

export class Maze {
  constructor(size) {
    this.size = size;
    // Walls stored as "x1,y1-x2,y2" where x1,y1 < x2,y2
    this.walls = new Set();
    // Initialize with outer border walls
    this.initializeBorders();
  }

  initializeBorders() {
    const n = this.size;
    // Top border: walls from (0,0)-(1,0) to (n-1,0)-(n,0)
    for (let x = 0; x < n; x++) {
      this.walls.add(this.wallKey(x, 0, x + 1, 0));
    }
    // Bottom border: walls from (0,n)-(1,n) to (n-1,n)-(n,n)
    for (let x = 0; x < n; x++) {
      this.walls.add(this.wallKey(x, n, x + 1, n));
    }
    // Left border: walls from (0,0)-(0,1) to (0,n-1)-(0,n)
    for (let y = 0; y < n; y++) {
      this.walls.add(this.wallKey(0, y, 0, y + 1));
    }
    // Right border: walls from (n,0)-(n,1) to (n,n-1)-(n,n)
    for (let y = 0; y < n; y++) {
      this.walls.add(this.wallKey(n, y, n, y + 1));
    }
  }

  wallKey(x1, y1, x2, y2) {
    // Ensure consistent ordering
    if (x1 > x2 || (x1 === x2 && y1 > y2)) {
      [x1, x2] = [x2, x1];
      [y1, y2] = [y2, y1];
    }
    return `${x1},${y1}-${x2},${y2}`;
  }

  hasWall(x1, y1, x2, y2) {
    return this.walls.has(this.wallKey(x1, y1, x2, y2));
  }

  isBorderWall(x1, y1, x2, y2) {
    if (x1 > x2 || (x1 === x2 && y1 > y2)) {
      [x1, x2] = [x2, x1];
      [y1, y2] = [y2, y1];
    }
    const n = this.size;
    const isTop = y1 === 0 && y2 === 0;
    const isBottom = y1 === n && y2 === n;
    const isLeft = x1 === 0 && x2 === 0;
    const isRight = x1 === n && x2 === n;
    return isTop || isBottom || isLeft || isRight;
  }

  toggleWall(x1, y1, x2, y2) {
    // Don't allow toggling border walls
    if (this.isBorderWall(x1, y1, x2, y2)) {
      return false;
    }
    
    const key = this.wallKey(x1, y1, x2, y2);
    if (this.walls.has(key)) {
      this.walls.delete(key);
      return false; // Wall removed
    } else {
      this.walls.add(key);
      return true; // Wall added
    }
  }

  // Get walls for a cell (for rendering)
  getCellWalls(x, y) {
    return {
      top: this.hasWall(x, y, x, y - 1),
      right: this.hasWall(x, y, x + 1, y),
      bottom: this.hasWall(x, y, x, y + 1),
      left: this.hasWall(x, y, x - 1, y)
    };
  }

  // Check if there's a wall between two adjacent cells
  hasWallBetween(x1, y1, x2, y2) {
    return this.hasWall(x1, y1, x2, y2);
  }

  // Get neighbors (cells without walls between)
  getNeighbors(x, y) {
    const neighbors = [];
    const directions = [
      { dx: 0, dy: -1, dir: 'top' },
      { dx: 1, dy: 0, dir: 'right' },
      { dx: 0, dy: 1, dir: 'bottom' },
      { dx: -1, dy: 0, dir: 'left' }
    ];

    for (const { dx, dy, dir } of directions) {
      const nx = x + dx;
      const ny = y + dy;
      if (nx >= 0 && nx < this.size && ny >= 0 && ny < this.size) {
        if (!this.hasWallBetween(x, y, nx, ny)) {
          neighbors.push({ x: nx, y: ny, direction: dir });
        }
      }
    }
    return neighbors;
  }

  generate() {
    // Use recursive backtracking to create a perfect maze
    const stack = [];
    const visited = new Set();

    const startX = 0;
    const startY = 0;
    visited.add(`${startX},${startY}`);
    stack.push({ x: startX, y: startY });

    // Clear all internal walls first
    this.walls.clear();
    this.initializeBorders();

    while (stack.length > 0) {
      const current = stack[stack.length - 1];
      
      // Get all unvisited neighbors
      const directions = [
        { dx: 0, dy: -1 }, // top
        { dx: 1, dy: 0 },  // right
        { dx: 0, dy: 1 },  // bottom
        { dx: -1, dy: 0 }  // left
      ];

      const unvisited = [];
      for (const { dx, dy } of directions) {
        const nx = current.x + dx;
        const ny = current.y + dy;
        if (nx >= 0 && nx < this.size && ny >= 0 && ny < this.size) {
          if (!visited.has(`${nx},${ny}`)) {
            unvisited.push({ x: nx, y: ny, dx, dy });
          }
        }
      }

      if (unvisited.length > 0) {
        // Choose random neighbor
        const next = unvisited[Math.floor(Math.random() * unvisited.length)];
        
        // Remove wall between current and next
        this.toggleWall(current.x, current.y, next.x, next.y);
        
        visited.add(`${next.x},${next.y}`);
        stack.push({ x: next.x, y: next.y });
      } else {
        stack.pop();
      }
    }
  }

  calculateComplexity() {
    let deadEnds = 0;
    let totalCells = this.size * this.size;

    for (let y = 0; y < this.size; y++) {
      for (let x = 0; x < this.size; x++) {
        const openPaths = this.getNeighbors(x, y).length;
        // Count dead ends (cells with only 1 opening, not start or end)
        if (openPaths === 1 && !(x === 0 && y === 0) && !(x === this.size - 1 && y === this.size - 1)) {
          deadEnds++;
        }
      }
    }

    return Math.min(100, Math.round((deadEnds / totalCells) * 100 * 3));
  }

  toGridString(startCell, endCell) {
    let grid = '';
    for (let y = 0; y < this.size; y++) {
      for (let x = 0; x < this.size; x++) {
        if (x === startCell?.x && y === startCell?.y) {
          grid += 'S';
        } else if (x === endCell?.x && y === endCell?.y) {
          grid += 'E';
        } else {
          grid += '·';
        }
      }
      grid += '\n';
    }
    return grid;
  }

  toWallString() {
    let walls = '';
    for (let y = 0; y < this.size; y++) {
      for (let x = 0; x < this.size; x++) {
        const cellWalls = this.getCellWalls(x, y);
        const wallCode = 
          (cellWalls.top ? '1' : '0') +
          (cellWalls.right ? '1' : '0') +
          (cellWalls.bottom ? '1' : '0') +
          (cellWalls.left ? '1' : '0');
        walls += wallCode + ' ';
      }
      walls += '\n';
    }
    return walls;
  }
}

/**
 * AI SOLVER
 */
export class AISolver {
  constructor() {
    this.apiKey = '';
    this.model = 'openai/gpt-4o';
    this.controller = null;
  }

  setApiKey(key) {
    this.apiKey = key;
  }

  setModel(model) {
    this.model = model;
  }

  async solve(maze, startCell, endCell, onProgress) {
    if (!this.apiKey) {
      throw new Error('OpenRouter API key is required');
    }

    this.controller = new AbortController();
    const prompt = this.createPrompt(maze, startCell, endCell);
    
    try {
      onProgress('Sending maze to AI...', 10);
      
      const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
          'Content-Type': 'application/json',
          'HTTP-Referer': window.location.href,
          'X-Title': 'Inception Maze Architect'
        },
        body: JSON.stringify({
          model: this.model,
          messages: [
            {
              role: 'system',
              content: 'You are a maze-solving AI. You must analyze the maze and provide the path from S (start) to E (end) as a sequence of coordinates. Output ONLY a JSON array of objects with "x" and "y" properties representing the path coordinates in order from start to end.'
            },
            {
              role: 'user',
              content: prompt
            }
          ],
          temperature: 0.1,
          max_tokens: 4000
        }),
        signal: this.controller.signal
      });

      onProgress('AI is thinking...', 40);

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error?.message || 'API request failed');
      }

      onProgress('Processing solution...', 70);

      const data = await response.json();
      const content = data.choices[0].message.content;
      
      onProgress('Parsing path...', 90);

      const path = this.parsePath(content);
      
      onProgress('Complete!', 100);
      
      return path;
    } catch (error) {
      if (error.name === 'AbortError') {
        throw new Error('Solving cancelled');
      }
      throw error;
    }
  }

  createPrompt(maze, startCell, endCell) {
    const { size } = maze;
    
    let prompt = `Solve this ${size}x${size} maze.\n\n`;
    prompt += `START (S): (${startCell.x}, ${startCell.y})\n`;
    prompt += `END (E): (${endCell.x}, ${endCell.y})\n\n`;
    prompt += `Grid (S=start, E=end, ·=empty cell):\n`;
    prompt += maze.toGridString(startCell, endCell);
    prompt += `\n`;
    prompt += `Wall encoding for each cell (TRBL = Top, Right, Bottom, Left, 1=wall, 0=open):\n`;
    prompt += maze.toWallString();
    prompt += `\n`;
    prompt += `Instructions:\n`;
    prompt += `1. Find a path from S to E\n`;
    prompt += `2. You can only move through open passages (0 in wall encoding)\n`;
    prompt += `3. Output ONLY a JSON array like: [{"x":0,"y":0},{"x":1,"y":0},...]\n`;
    prompt += `4. Include all coordinates in the path from start to end\n`;
    prompt += `5. Do not include any explanation, only the JSON array\n`;
    
    return prompt;
  }

  parsePath(content) {
    const jsonMatch = content.match(/\[[\s\S]*\]/);
    if (jsonMatch) {
      try {
        const path = JSON.parse(jsonMatch[0]);
        if (Array.isArray(path) && path.every(p => typeof p.x === 'number' && typeof p.y === 'number')) {
          return path;
        }
      } catch (e) {
        console.error('Failed to parse JSON:', e);
      }
    }
    
    const coordPattern = /\((\d+)\s*,\s*(\d+)\)|(\d+)\s+(\d+)|"x":\s*(\d+)[^}]*"y":\s*(\d+)/g;
    const path = [];
    let match;
    
    while ((match = coordPattern.exec(content)) !== null) {
      const x = parseInt(match[1] || match[3] || match[5]);
      const y = parseInt(match[2] || match[4] || match[6]);
      if (!isNaN(x) && !isNaN(y)) {
        path.push({ x, y });
      }
    }
    
    if (path.length === 0) {
      throw new Error('Could not parse AI response. The AI returned an invalid format.');
    }
    
    return path;
  }

  cancel() {
    if (this.controller) {
      this.controller.abort();
    }
  }
}
