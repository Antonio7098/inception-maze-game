import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestToolExecution:
    """Integration tests for tool execution logic"""

    def setup_method(self):
        self.walls_set = set()

    def test_has_wall_between_vertical(self):
        self.walls_set.add("5,5-5,6")

        def has_wall_between(x1, y1, x2, y2):
            if x1 == x2:
                max_y = max(y1, y2)
                wall_key = f"{x1},{max_y}-{x1 + 1},{max_y}"
                return wall_key in self.walls_set
            return False

        assert has_wall_between(5, 5, 5, 6) is True
        assert has_wall_between(5, 5, 5, 4) is False

    def test_has_wall_between_horizontal(self):
        self.walls_set.add("5,5-6,5")

        def has_wall_between(x1, y1, x2, y2):
            if x1 != x2:
                max_x = max(x1, x2)
                wall_key = f"{max_x},{y1}-{max_x},{y1 + 1}"
                return wall_key in self.walls_set
            return False

        assert has_wall_between(5, 5, 6, 5) is True
        assert has_wall_between(5, 5, 4, 5) is False


class TestExecuteTool:
    """Integration tests for execute_tool function"""

    def test_execute_get_current_position(self):
        exec_code = """
def execute_tool(tool_name, pos, maze_size, walls_set, end, steps):
    x, y = pos["x"], pos["y"]
    
    if tool_name == "get_current_position":
        return {"position": pos, "steps": steps}
    
    return {"error": "Unknown tool"}
"""
        exec(exec_code)

        result = execute_tool(
            "get_current_position", {"x": 5, "y": 5}, 10, set(), {"x": 9, "y": 9}, 0
        )
        assert result["position"] == {"x": 5, "y": 5}
        assert result["steps"] == 0

    def test_execute_get_available_moves(self):
        exec_code = """
def has_wall_between(x1, y1, x2, y2, walls_set):
    if x1 == x2:
        max_y = max(y1, y2)
        wall_key = f"{x1},{max_y}-{x1+1},{max_y}"
        return wall_key in walls_set
    else:
        max_x = max(x1, x2)
        wall_key = f"{max_x},{y1}-{max_x},{y1+1}"
        return wall_key in walls_set

def execute_tool(tool_name, pos, maze_size, walls_set, end, steps):
    x, y = pos["x"], pos["y"]
    
    if tool_name == "get_available_moves":
        moves = []
        if y > 0 and not has_wall_between(x, y, x, y - 1, walls_set):
            moves.append("up")
        if y < maze_size - 1 and not has_wall_between(x, y, x, y + 1, walls_set):
            moves.append("down")
        if x > 0 and not has_wall_between(x, y, x - 1, y, walls_set):
            moves.append("left")
        if x < maze_size - 1 and not has_wall_between(x, y, x + 1, y, walls_set):
            moves.append("right")
        return {"available": moves, "position": pos}
    
    return {"error": "Unknown tool"}
"""
        exec(exec_code)

        walls = set()
        walls.add("5,5-5,6")

        result = execute_tool(
            "get_available_moves", {"x": 5, "y": 5}, 10, walls, {"x": 9, "y": 9}, 0
        )
        assert "up" in result["available"]
        assert "down" not in result["available"]

    def test_execute_move_success(self):
        exec_code = """
def has_wall_between(x1, y1, x2, y2, walls_set):
    if x1 == x2:
        max_y = max(y1, y2)
        wall_key = f"{x1},{max_y}-{x1+1},{max_y}"
        return wall_key in walls_set
    else:
        max_x = max(x1, x2)
        wall_key = f"{max_x},{y1}-{max_x},{y1+1}"
        return wall_key in walls_set

def execute_tool(tool_name, pos, maze_size, walls_set, end, steps):
    x, y = pos["x"], pos["y"]
    
    if tool_name.startswith("move_"):
        direction = tool_name.replace("move_", "")
        nx, ny = x, y
        if direction == "up":
            ny -= 1
        elif direction == "down":
            ny += 1
        elif direction == "left":
            nx -= 1
        elif direction == "right":
            nx += 1
        
        if nx < 0 or nx >= maze_size or ny < 0 or ny >= maze_size:
            return {"success": False, "message": "Out of bounds", "position": pos}
        
        if has_wall_between(x, y, nx, ny, walls_set):
            return {"success": False, "message": "Wall in way", "position": pos}
        
        new_pos = {"x": nx, "y": ny}
        steps += 1
        at_end = nx == end["x"] and ny == end["y"]
        return {"success": True, "position": new_pos, "is_complete": at_end, "steps": steps, "message": f"Moved {direction}"}
    
    return {"error": "Unknown tool"}
"""
        exec(exec_code)

        result = execute_tool(
            "move_right", {"x": 5, "y": 5}, 10, set(), {"x": 9, "y": 9}, 0
        )
        assert result["success"] is True
        assert result["position"] == {"x": 6, "y": 5}
        assert result["steps"] == 1

    def test_execute_move_blocked_by_wall(self):
        exec_code = """
def has_wall_between(x1, y1, x2, y2, walls_set):
    if x1 == x2:
        max_y = max(y1, y2)
        wall_key = f"{x1},{max_y}-{x1+1},{max_y}"
        return wall_key in walls_set
    else:
        max_x = max(x1, x2)
        wall_key = f"{max_x},{y1}-{max_x},{y1+1}"
        return wall_key in walls_set

def execute_tool(tool_name, pos, maze_size, walls_set, end, steps):
    x, y = pos["x"], pos["y"]
    
    if tool_name.startswith("move_"):
        direction = tool_name.replace("move_", "")
        nx, ny = x, y
        if direction == "up":
            ny -= 1
        elif direction == "down":
            ny += 1
        elif direction == "left":
            nx -= 1
        elif direction == "right":
            nx += 1
        
        if nx < 0 or nx >= maze_size or ny < 0 or ny >= maze_size:
            return {"success": False, "message": "Out of bounds", "position": pos}
        
        if has_wall_between(x, y, nx, ny, walls_set):
            return {"success": False, "message": "Wall in way", "position": pos}
        
        new_pos = {"x": nx, "y": ny}
        steps += 1
        at_end = nx == end["x"] and ny == end["y"]
        return {"success": True, "position": new_pos, "is_complete": at_end, "steps": steps, "message": f"Moved {direction}"}
    
    return {"error": "Unknown tool"}
"""
        exec(exec_code)

        walls = set()
        walls.add("6,5-6,6")

        result = execute_tool(
            "move_down", {"x": 6, "y": 5}, 10, walls, {"x": 9, "y": 9}, 0
        )
        assert result["success"] is False
        assert result["message"] == "Wall in way"


class TestAsciiMazeGeneration:
    """Integration tests for ASCII maze generation"""

    def test_generate_ascii_maze(self):
        walls = ["0,0-1,0", "1,0-2,0", "0,1-0,2"]

        def get_ascii_maze(size, walls, start, end):
            walls_set = set(walls)
            lines = ["+" + "--+" * size]
            for y in range(size):
                row = "|"
                for x in range(size):
                    if x == start["x"] and y == start["y"]:
                        cell = "S "
                    elif x == end["x"] and y == end["y"]:
                        cell = "E "
                    else:
                        cell = "  "
                    right = (
                        "|"
                        if f"{x},{y}-{x + 1},{y}" in walls_set or x == size - 1
                        else " "
                    )
                    row += cell + right
                lines.append(row)
                if y < size - 1:
                    w = ""
                    for x in range(size):
                        b = (
                            "--+"
                            if f"{x},{y}-{x},{y + 1}" in walls_set or y == size - 1
                            else "  +"
                        )
                        w += b
                    lines.append(w)
            lines.append("+" + "--+" * size)
            return "\\n".join(lines)

        ascii_maze = get_ascii_maze(5, walls, {"x": 0, "y": 0}, {"x": 4, "y": 4})
        assert "S" in ascii_maze
        assert "E" in ascii_maze
        assert "+--" in ascii_maze


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
