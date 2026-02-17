import { describe, it, expect, beforeEach } from 'vitest'
import { Maze, CONFIG } from './maze/mazeLogic'

describe('Maze Logic', () => {
  describe('Maze constructor', () => {
    it('should create a maze with correct size', () => {
      const maze = new Maze(10)
      expect(maze.size).toBe(10)
    })

    it('should initialize with border walls', () => {
      const maze = new Maze(10)
      expect(maze.walls.size).toBeGreaterThan(0)
    })
  })

  describe('wallKey', () => {
    it('should normalize coordinates', () => {
      const maze = new Maze(10)
      const key1 = maze.wallKey(0, 0, 1, 0)
      const key2 = maze.wallKey(1, 0, 0, 0)
      expect(key1).toBe(key2)
    })

    it('should format key correctly', () => {
      const maze = new Maze(10)
      const key = maze.wallKey(5, 5, 6, 5)
      expect(key).toBe('5,5-6,5')
    })
  })

  describe('hasWall', () => {
    it('should detect existing wall', () => {
      const maze = new Maze(10)
      maze.walls.add('5,5-6,5')
      expect(maze.hasWall(5, 5, 6, 5)).toBe(true)
    })

    it('should return false for non-existent wall', () => {
      const maze = new Maze(10)
      expect(maze.hasWall(5, 5, 6, 5)).toBe(false)
    })
  })

  describe('toggleWall', () => {
    it('should add a wall', () => {
      const maze = new Maze(10)
      const initialSize = maze.walls.size
      maze.toggleWall(5, 5, 6, 5)
      expect(maze.walls.size).toBe(initialSize + 1)
    })

    it('should remove existing wall', () => {
      const maze = new Maze(10)
      maze.toggleWall(5, 5, 6, 5)
      const sizeAfterAdd = maze.walls.size
      maze.toggleWall(5, 5, 6, 5)
      expect(maze.walls.size).toBe(sizeAfterAdd - 1)
    })

    it('should not allow toggling border walls', () => {
      const maze = new Maze(10)
      const initialSize = maze.walls.size
      const result = maze.toggleWall(0, 0, 1, 0)
      expect(result).toBe(false)
      expect(maze.walls.size).toBe(initialSize)
    })
  })

  describe('generate', () => {
    it('should generate a maze', () => {
      const maze = new Maze(10)
      maze.generate()
      expect(maze.walls.size).toBeGreaterThan(0)
    })

    it('should create different mazes', () => {
      const maze1 = new Maze(10)
      maze1.generate()
      const maze2 = new Maze(10)
      maze2.generate()
      expect(maze1.walls.size).toBeGreaterThan(0)
    })
  })

  describe('calculateComplexity', () => {
    it('should return a value between 0 and 100', () => {
      const maze = new Maze(10)
      maze.generate()
      const complexity = maze.calculateComplexity()
      expect(complexity).toBeGreaterThanOrEqual(0)
      expect(complexity).toBeLessThanOrEqual(100)
    })
  })

  describe('getNeighbors', () => {
    it('should return valid neighbors', () => {
      const maze = new Maze(10)
      maze.generate()
      const neighbors = maze.getNeighbors(5, 5)
      neighbors.forEach(n => {
        expect(n.x).toBeGreaterThanOrEqual(0)
        expect(n.x).toBeLessThan(10)
        expect(n.y).toBeGreaterThanOrEqual(0)
        expect(n.y).toBeLessThan(10)
      })
    })
  })
})

describe('CONFIG', () => {
  it('should have all required themes', () => {
    expect(CONFIG.themes).toContain('limbo')
    expect(CONFIG.themes).toContain('hotel')
    expect(CONFIG.themes).toContain('snow')
  })

  it('should have theme names', () => {
    expect(CONFIG.themeNames.limbo).toBeDefined()
    expect(CONFIG.themeNames.hotel).toBeDefined()
    expect(CONFIG.themeNames.snow).toBeDefined()
  })

  it('should have colors for each theme', () => {
    CONFIG.themes.forEach(theme => {
      expect(CONFIG.colors[theme]).toBeDefined()
      expect(CONFIG.colors[theme].wall).toBeDefined()
      expect(CONFIG.colors[theme].start).toBeDefined()
      expect(CONFIG.colors[theme].end).toBeDefined()
    })
  })
})
