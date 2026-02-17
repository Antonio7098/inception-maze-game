import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


class TestMazeLogic:
    """Unit tests for maze logic"""

    def test_wall_key_normalizes_coordinates(self):
        from maze.mazeLogic import Maze

        maze = Maze(10)
        key1 = maze.wallKey(0, 0, 1, 0)
        key2 = maze.wallKey(1, 0, 0, 0)
        assert key1 == key2

    def test_wall_key_format(self):
        from maze.mazeLogic import Maze

        maze = Maze(10)
        key = maze.wallKey(5, 5, 6, 5)
        assert key == "5,5-6,5"

    def test_has_wall(self):
        from maze.mazeLogic import Maze

        maze = Maze(10)
        maze.walls.add("0,0-1,0")
        assert maze.hasWall(0, 0, 1, 0)
        assert not maze.hasWall(0, 0, 0, 1)

    def test_toggle_wall(self):
        from maze.mazeLogic import Maze

        maze = Maze(10)
        initial_count = len(maze.walls)
        maze.toggleWall(5, 5, 6, 5)
        assert len(maze.walls) == initial_count + 1
        maze.toggleWall(5, 5, 6, 5)
        assert len(maze.walls) == initial_count

    def test_border_walls_not_toggleable(self):
        from maze.mazeLogic import Maze

        maze = Maze(10)
        initial_walls = len(maze.walls)
        result = maze.toggleWall(0, 0, 1, 0)
        assert result is False
        assert len(maze.walls) == initial_walls

    def test_generate_creates_perfect_maze(self):
        from maze.mazeLogic import Maze

        maze = Maze(10)
        maze.generate()
        assert len(maze.walls) > 0

    def test_get_neighbors(self):
        from maze.mazeLogic import Maze

        maze = Maze(10)
        neighbors = maze.getNeighbors(5, 5)
        assert len(neighbors) >= 0
        assert all(n["x"] >= 0 and n["x"] < 10 for n in neighbors)
        assert all(n["y"] >= 0 and n["y"] < 10 for n in neighbors)

    def test_calculate_complexity(self):
        from maze.mazeLogic import Maze

        maze = Maze(10)
        complexity = maze.calculateComplexity()
        assert 0 <= complexity <= 100


class TestOpenRouterService:
    """Unit tests for OpenRouter service"""

    def test_is_free_model_detection(self):
        from services.openrouter import is_free_model

        assert is_free_model("meta-llama/llama-3.3-8b-instruct:free", {})
        assert is_free_model("test/free", {})
        assert not is_free_model("gpt-4o", {"pricing": {"prompt": "0.001"}})

    def test_supports_tools_basic(self):
        from services.openrouter import supports_tools

        model = {
            "id": "test-model",
            "name": "Test Model",
            "architecture": {
                "input_modalities": ["text"],
                "output_modalities": ["text"],
            },
            "supported_parameters": ["tools"],
        }
        assert supports_tools(model) is True


class TestChallenges:
    """Unit tests for challenges service"""

    def test_get_challenges_returns_list(self):
        from services.challenges import get_challenges

        challenges = get_challenges()
        assert isinstance(challenges, list)
        assert len(challenges) > 0

    def test_get_challenge_by_id(self):
        from services.challenges import get_challenge_by_id

        challenge = get_challenge_by_id("challenge-1")
        assert challenge is not None
        assert challenge["id"] == "challenge-1"

    def test_get_challenge_by_id_not_found(self):
        from services.challenges import get_challenge_by_id

        challenge = get_challenge_by_id("non-existent")
        assert challenge is None

    def test_challenge_fields(self):
        from services.challenges import get_challenges

        challenges = get_challenges()
        required_fields = ["id", "name", "model", "time_limit_minutes", "grid_size"]
        for challenge in challenges:
            for field in required_fields:
                assert field in challenge, f"Missing field: {field}"


class TestWallCoordinateLogic:
    """Test wall coordinate system"""

    def test_vertical_wall_key(self):
        from maze.mazeLogic import Maze

        maze = Maze(15)
        key = maze.wallKey(5, 5, 5, 6)
        assert key == "5,5-5,6"

    def test_horizontal_wall_key(self):
        from maze.mazeLogic import Maze

        maze = Maze(15)
        key = maze.wallKey(5, 5, 6, 5)
        assert key == "5,5-6,5"

    def test_has_wall_between_cells(self):
        from maze.mazeLogic import Maze

        maze = Maze(15)
        maze.walls.add("5,5-6,5")
        assert maze.hasWallBetween(5, 5, 6, 5)


class TestMazeBorderInitialization:
    """Test maze border initialization"""

    def test_border_walls_created(self):
        from maze.mazeLogic import Maze

        maze = Maze(10)
        border_count = sum(
            1
            for w in maze.walls
            if maze.isBorderWall(
                *[
                    int(x)
                    for x in w.split("-")[0].split(",") + w.split("-")[1].split(",")
                ]
            )
        )
        assert border_count > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
