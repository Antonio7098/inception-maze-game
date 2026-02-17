"""
Maze Agent Service
Core agent logic using OpenAI SDK with function calling
"""

import json
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator, Callable
from datetime import datetime

from openai import OpenAI
from pydantic import BaseModel

from ..models.schemas import (
    MazeModel,
    MazePosition,
    ErrorTaxonomy,
    MazeAgentError,
    ErrorCode,
    EventType,
)
from ..utils.logging import StructuredLogger, EventLogger


# ============================================
# TOOL DEFINITIONS
# ============================================


class MazeTools:
    """Tool definitions for the agent"""

    @staticmethod
    def get_tools() -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_current_position",
                    "description": "Get your current position in the maze and see surrounding cells",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "move_up",
                    "description": "Move up in the maze (decreases Y coordinate)",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "move_down",
                    "description": "Move down in the maze (increases Y coordinate)",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "move_left",
                    "description": "Move left in the maze (decreases X coordinate)",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "move_right",
                    "description": "Move right in the maze (increases X coordinate)",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_available_moves",
                    "description": "Check which directions are available for movement from current position",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "check_goal",
                    "description": "Check if you have reached the end/goal of the maze",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
        ]


# ============================================
# MAZE REPRESENTATION
# ============================================


class MazeRepresentation:
    """Generate maze representations for the LLM"""

    @staticmethod
    def get_ascii_maze(maze: MazeModel) -> str:
        """Generate ASCII art representation of maze"""
        size = maze.size
        lines = []

        # Top border
        lines.append("┌" + "──┬" * (size - 1) + "──┐")

        for y in range(size):
            row = "│"
            for x in range(size):
                # Determine cell content
                if x == maze.start.x and y == maze.start.y:
                    cell = "S "
                elif x == maze.end.x and y == maze.end.y:
                    cell = "E "
                else:
                    cell = "  "

                # Check right wall
                wall_key = f"{x},{y}-{x + 1},{y}" if x < size - 1 else None
                right_wall = "│" if wall_key in maze.walls else " "
                row += cell + right_wall

            lines.append(row)

            # Bottom walls (except last row)
            if y < size - 1:
                wall_row = ""
                for x in range(size):
                    wall_key = f"{x},{y}-{x},{y + 1}" if y < size - 1 else None
                    bottom_wall = "──┼" if wall_key in maze.walls else "  ┼"
                    wall_row += bottom_wall
                wall_row = wall_row[:-1] + "┤"
                lines.append(wall_row)

        # Bottom border
        lines.append("└" + "──┴" * (size - 1) + "──┘")

        return "\n".join(lines)

    @staticmethod
    def get_wall_data(maze: MazeModel) -> str:
        """Get wall data as readable text"""
        lines = []
        for y in range(maze.size):
            row_data = []
            for x in range(maze.size):
                # Determine walls
                top = "1" if f"{x},{y}-{x},{y - 1}" in maze.walls or y == 0 else "0"
                right = (
                    "1"
                    if f"{x},{y}-{x + 1},{y}" in maze.walls or x == maze.size - 1
                    else "0"
                )
                bottom = (
                    "1"
                    if f"{x},{y}-{x},{y + 1}" in maze.walls or y == maze.size - 1
                    else "0"
                )
                left = "1" if f"{x},{y}-{x - 1},{y}" in maze.walls or x == 0 else "0"
                row_data.append(f"({x},{y}):[{top},{right},{bottom},{left}]")
            lines.append(" ".join(row_data))
        return "\n".join(lines)


# ============================================
# MAZE AGENT SERVICE
# ============================================


class MazeAgentService:
    """
    Maze solving agent service
    Uses OpenAI function calling for navigation
    """

    def __init__(
        self,
        api_key: str,
        model: str = "openai/gpt-4o",
        max_iterations: int = 500,
        base_url: str = "https://openrouter.ai/api/v1",
    ):
        self.api_key = api_key
        self.model = model
        self.max_iterations = max_iterations

        # Initialize OpenAI client
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=120.0,
            max_retries=2,
            default_headers={
                "HTTP-Referer": "https://maze-agent.example.com",
                "X-Title": "Inception Maze Agent",
            },
        )

        # Agent state
        self.maze = None
        self.current_position = None
        self.path: List[Dict[str, int]] = []
        self.visited: set = set()
        self.step_count = 0
        self.is_complete = False
        self.messages: List[Dict] = []

        # Loggers
        self.structured_logger: Optional[StructuredLogger] = None
        self.event_logger: Optional[EventLogger] = None

    def set_loggers(
        self, structured_logger: StructuredLogger, event_logger: EventLogger
    ):
        self.structured_logger = structured_logger
        self.event_logger = event_logger

    def _log(
        self, level: str, category: str, code: str, message: str, data: Dict = None
    ):
        """Log to both loggers"""
        if self.structured_logger:
            getattr(self.structured_logger, level.lower())(
                category, code, message, data
            )
        if self.event_logger:
            self.event_logger.log(level, category, code, message, data)

    async def solve(
        self, maze: MazeModel, on_event: Callable[[Dict], None]
    ) -> AsyncGenerator[Dict, None]:
        """
        Solve the maze using the agent
        Yields events for SSE streaming
        """
        self.maze = maze
        self.current_position = {"x": maze.start.x, "y": maze.start.y}
        self.path = [dict(self.current_position)]
        self.visited = {f"{maze.start.x},{maze.start.y}"}
        self.step_count = 0
        self.is_complete = False

        # Setup loggers
        event_logger = EventLogger(on_event)
        structured_logger = StructuredLogger(
            "maze_agent",
            on_log=lambda e: on_event({"event": EventType.LOG.value, "data": e}),
        )
        self.set_loggers(structured_logger, event_logger)

        self._log(
            "info",
            "AGENT",
            "INIT",
            f"Starting agent solver for {maze.size}x{maze.size} maze",
            {
                "start": maze.start.model_dump(),
                "end": maze.end.model_dump(),
                "model": self.model,
            },
        )

        # Generate initial prompts
        system_prompt, user_prompt = self._build_prompts(maze)

        # Emit prompt event for observability
        event_logger.prompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=MazeTools.get_tools(),
            model=self.model,
        )

        yield {
            "event": EventType.PROMPT.value,
            "data": {
                "system_prompt": system_prompt[:500] + "...",
                "user_prompt": user_prompt[:500] + "...",
                "model": self.model,
                "tools_count": len(MazeTools.get_tools()),
            },
        }

        # Initialize messages
        self.messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        event_logger.init(
            message="Agent initialized, starting solve",
            maze_size=maze.size,
            model=self.model,
        )
        yield {"event": EventType.INIT.value, "data": {"message": "Agent initialized"}}

        # Main solving loop
        iteration = 0
        last_tool_result = None

        while not self.is_complete and iteration < self.max_iterations:
            iteration += 1

            self._log(
                "debug",
                "AGENT",
                "ITERATION",
                f"Starting iteration {iteration}",
                {"position": self.current_position, "is_complete": self.is_complete},
            )

            try:
                # Make API call
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    tools=MazeTools.get_tools(),
                    tool_choice="auto",
                    temperature=0.3,
                    max_tokens=2000,
                )

                assistant_message = response.choices[0].message

                # Handle tool calls
                if assistant_message.tool_calls:
                    for tool_call in assistant_message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_call_id = tool_call.id

                        self._log(
                            "info",
                            "TOOL",
                            "CALL",
                            f"Executing tool: {tool_name}",
                            {
                                "tool_call_id": tool_call_id,
                                "position": self.current_position,
                            },
                        )

                        event_logger.tool_call(
                            tool_name, self.current_position, self.step_count
                        )
                        yield {
                            "event": EventType.TOOL_CALL.value,
                            "data": {
                                "tool_name": tool_name,
                                "tool_call_id": tool_call_id,
                                "position": self.current_position,
                                "step_count": self.step_count,
                            },
                        }

                        # Execute tool
                        try:
                            result = self._execute_tool(tool_name)
                            last_tool_result = result

                            self._log(
                                "info",
                                "TOOL",
                                "RESULT",
                                f"Tool {tool_name} result",
                                result,
                            )

                            event_logger.tool_result(
                                tool_name, result, result.get("success", True)
                            )
                            yield {
                                "event": EventType.TOOL_RESULT.value,
                                "data": {
                                    "tool_name": tool_name,
                                    "tool_call_id": tool_call_id,
                                    "result": result,
                                    "success": result.get("success", True),
                                },
                            }

                            # Add to messages
                            self.messages.append(
                                {
                                    "role": "assistant",
                                    "content": assistant_message.content,
                                    "tool_calls": [
                                        {
                                            "id": tool_call_id,
                                            "type": "function",
                                            "function": {
                                                "name": tool_name,
                                                "arguments": tool_call.function.arguments,
                                            },
                                        }
                                    ],
                                }
                            )

                            self.messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_call_id,
                                    "content": json.dumps(result),
                                }
                            )

                            # Check if complete
                            if tool_name.startswith("move_") and result.get(
                                "is_complete"
                            ):
                                self.is_complete = True
                                self._log(
                                    "info",
                                    "AGENT",
                                    "COMPLETE",
                                    "Maze solved!",
                                    {
                                        "steps": self.step_count,
                                        "path_length": len(self.path),
                                    },
                                )

                        except Exception as e:
                            self._log(
                                "error",
                                "TOOL",
                                "FAILED",
                                f"Tool execution failed: {str(e)}",
                            )
                            event_logger.error(
                                ErrorCode.TOOL_EXECUTION_FAILED.value, str(e)
                            )
                            yield {
                                "event": EventType.ERROR.value,
                                "data": {
                                    "code": ErrorCode.TOOL_EXECUTION_FAILED.value,
                                    "message": str(e),
                                },
                            }

                else:
                    # Text response (no tool call)
                    self.messages.append(
                        {"role": "assistant", "content": assistant_message.content}
                    )

                    # Check if agent thinks it's done
                    if assistant_message.content and (
                        "solved" in assistant_message.content.lower()
                        or "complete" in assistant_message.content.lower()
                    ):
                        self.is_complete = True

                # Check for loops
                if self._detect_loop():
                    self._log("warn", "AGENT", "LOOP", "Agent appears stuck in loop")
                    event_logger.error(
                        ErrorCode.LOOP_DETECTED.value, "Agent stuck in loop"
                    )
                    yield {
                        "event": EventType.ERROR.value,
                        "data": {
                            "code": ErrorCode.LOOP_DETECTED.value,
                            "message": "Agent stuck in loop",
                        },
                    }
                    break

                # Emit position update
                event_logger.position(
                    self.current_position, self.step_count, self.path, self.is_complete
                )
                yield {
                    "event": EventType.POSITION_UPDATE.value,
                    "data": {
                        "position": self.current_position,
                        "step_count": self.step_count,
                        "path": self.path,
                        "is_complete": self.is_complete,
                    },
                }

                # Small delay for rate limiting
                await asyncio.sleep(0.1)

            except Exception as e:
                self._log("error", "AGENT", "ERROR", f"Solve error: {str(e)}")
                event_logger.error(
                    ErrorCode.AGENT_ERROR.value
                    if hasattr(ErrorCode, "AGENT_ERROR")
                    else "AGENT_ERROR",
                    str(e),
                )
                yield {
                    "event": EventType.ERROR.value,
                    "data": {"code": "AGENT_ERROR", "message": str(e)},
                }
                break

        # Final completion event
        event_logger.complete(self.is_complete, self.path, self.step_count)
        yield {
            "event": EventType.COMPLETE.value,
            "data": {
                "success": self.is_complete,
                "path": self.path,
                "steps": self.step_count,
                "iterations": iteration,
                "logs": structured_logger.get_logs(),
            },
        }

    def _build_prompts(self, maze: MazeModel) -> tuple:
        """Build system and user prompts"""

        ascii_maze = MazeRepresentation.get_ascii_maze(maze)
        wall_data = MazeRepresentation.get_wall_data(maze)

        system_prompt = f"""You are a maze-solving agent. You must navigate from START to END using the available tools.

MAZE INFORMATION:
- Grid size: {maze.size}x{maze.size}
- Start position: ({maze.start.x}, {maze.start.y})
- End position: ({maze.end.x}, {maze.end.y})

MAZE MAP (S=Start, E=End):
{ascii_maze}

WALL DATA (for each cell x,y: [top, right, bottom, left], 1=wall, 0=open):
{wall_data}

YOUR GOAL: Reach the END position at ({maze.end.x}, {maze.end.y})

AVAILABLE TOOLS:
1. get_current_position - See where you are and the maze around you  
2. move_up, move_down, move_left, move_right - Move in a direction
3. get_available_moves - Check which directions are open from current position
4. check_goal - Check if you've reached the end

STRATEGY:
1. Use the maze map above to plan your optimal path
2. Use move tools to navigate step by step
3. After each move, verify with get_available_moves
4. Call check_goal when you think you might be at the end

IMPORTANT:
- You have the FULL maze information above - use it to plan!
- Move one step at a time
- Always check if your move was successful
- If you hit a wall, use a different direction
- The goal is at ({maze.end.x}, {maze.end.y})"""

        user_prompt = f"Start solving the maze! You're at ({maze.start.x}, {maze.start.y}) and need to reach ({maze.end.x}, {maze.end.y}). Begin by exploring your surroundings."

        return system_prompt, user_prompt

    def _execute_tool(self, tool_name: str) -> Dict[str, Any]:
        """Execute a tool and return result"""

        if tool_name == "get_current_position":
            return {
                "position": self.current_position,
                "path": self.path,
                "visited": list(self.visited),
                "end_position": {"x": self.maze.end.x, "y": self.maze.end.y},
            }

        elif tool_name == "move_up":
            return self._move("up")
        elif tool_name == "move_down":
            return self._move("down")
        elif tool_name == "move_left":
            return self._move("left")
        elif tool_name == "move_right":
            return self._move("right")

        elif tool_name == "get_available_moves":
            moves = []
            x, y = self.current_position["x"], self.current_position["y"]

            # Check each direction
            if y > 0 and not self._has_wall(x, y, x, y - 1):
                moves.append("up")
            if y < self.maze.size - 1 and not self._has_wall(x, y, x, y + 1):
                moves.append("down")
            if x > 0 and not self._has_wall(x, y, x - 1, y):
                moves.append("left")
            if x < self.maze.size - 1 and not self._has_wall(x, y, x + 1, y):
                moves.append("right")

            return {"available": moves, "position": self.current_position}

        elif tool_name == "check_goal":
            at_end = (
                self.current_position["x"] == self.maze.end.x
                and self.current_position["y"] == self.maze.end.y
            )
            return {
                "is_complete": at_end,
                "position": self.current_position,
                "end_position": {"x": self.maze.end.x, "y": self.maze.end.y},
                "steps_taken": self.step_count,
            }

        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    def _move(self, direction: str) -> Dict[str, Any]:
        """Move in a direction"""

        if self.is_complete:
            return {
                "success": False,
                "message": "Already at end",
                "position": self.current_position,
            }

        if self.step_count >= self.max_iterations:
            return {
                "success": False,
                "message": "Maximum steps reached",
                "position": self.current_position,
            }

        # Calculate new position
        x, y = self.current_position["x"], self.current_position["y"]
        new_x, new_y = x, y

        if direction == "up":
            new_y -= 1
        elif direction == "down":
            new_y += 1
        elif direction == "left":
            new_x -= 1
        elif direction == "right":
            new_x += 1

        # Check bounds
        if new_x < 0 or new_x >= self.maze.size or new_y < 0 or new_y >= self.maze.size:
            return {
                "success": False,
                "message": f"Cannot move {direction}, would go out of bounds",
                "position": self.current_position,
            }

        # Check wall
        if self._has_wall(x, y, new_x, new_y):
            return {
                "success": False,
                "message": f"Cannot move {direction}, wall in the way",
                "position": self.current_position,
            }

        # Move successful
        self.current_position = {"x": new_x, "y": new_y}
        self.path.append(dict(self.current_position))
        self.visited.add(f"{new_x},{new_y}")
        self.step_count += 1

        # Check if at end
        is_at_end = new_x == self.maze.end.x and new_y == self.maze.end.y

        return {
            "success": True,
            "message": f"Moved {direction} to ({new_x}, {new_y})",
            "position": self.current_position,
            "is_complete": is_at_end,
            "steps_taken": self.step_count,
        }

    def _has_wall(self, x1: int, y1: int, x2: int, y2: int) -> bool:
        """Check if there's a wall between two cells"""
        # Create wall key (always smaller coordinate first)
        if x1 > x2 or y1 > y2:
            x1, x2 = x2, x1
            y1, y2 = y2, y1

        wall_key = f"{x1},{y1}-{x2},{y2}"

        # Check outer walls
        if wall_key in self.maze.walls:
            return True

        # Check if it's an outer boundary
        if x1 == 0 and x2 == 0:  # Left boundary
            return True
        if x1 == self.maze.size - 1 and x2 == self.maze.size - 1:  # Right boundary
            return True
        if y1 == 0 and y2 == 0:  # Top boundary
            return True
        if y1 == self.maze.size - 1 and y2 == self.maze.size - 1:  # Bottom boundary
            return True

        return False

    def _detect_loop(self) -> bool:
        """Detect if agent is stuck in a loop"""
        if len(self.path) < 6:
            return False

        recent = [f"{p['x']},{p['y']}" for p in self.path[-6:]]

        # Check for repeating patterns
        for i in range(len(recent) - 2):
            if recent[i] == recent[i + 3] and recent[i + 1] == recent[i + 2]:
                return True

        return False
