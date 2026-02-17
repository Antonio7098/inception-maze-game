"""
Pydantic Models for Maze Agent API
Following SOLID principles with clear separation of concerns
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
from datetime import datetime
import json


# ============================================
# ENUMS
# ============================================


class EventType(str, Enum):
    """Event types for SSE streaming"""

    INIT = "init"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    POSITION_UPDATE = "position_update"
    LOG = "log"
    ERROR = "error"
    COMPLETE = "complete"
    PROMPT = "prompt"  # Full prompt sent to LLM


class ErrorCategory(str, Enum):
    """Error categories for taxonomy"""

    AUTH = "AUTH"
    NETWORK = "NETWORK"
    VALIDATION = "VALIDATION"
    MAZE = "MAZE"
    AGENT = "AGENT"
    INTERNAL = "INTERNAL"


class ErrorCode(str, Enum):
    """Detailed error codes"""

    # Auth errors
    INVALID_API_KEY = "AUTH_INVALID_API_KEY"
    MISSING_API_KEY = "AUTH_MISSING_API_KEY"
    RATE_LIMITED = "AUTH_RATE_LIMITED"

    # Network errors
    CONNECTION_FAILED = "NETWORK_CONNECTION_FAILED"
    TIMEOUT = "NETWORK_TIMEOUT"
    REQUEST_FAILED = "NETWORK_REQUEST_FAILED"

    # Validation errors
    INVALID_MAZE = "VALIDATION_INVALID_MAZE"
    INVALID_POSITION = "VALIDATION_INVALID_POSITION"
    SCHEMA_MISMATCH = "VALIDATION_SCHEMA_MISMATCH"

    # Maze errors
    NO_PATH = "MAZE_NO_PATH"
    START_BLOCKED = "MAZE_START_BLOCKED"
    END_BLOCKED = "MAZE_END_BLOCKED"

    # Agent errors
    MAX_STEPS_REACHED = "AGENT_MAX_STEPS_REACHED"
    INVALID_TOOL_CALL = "AGENT_INVALID_TOOL_CALL"
    TOOL_EXECUTION_FAILED = "AGENT_TOOL_EXECUTION_FAILED"
    LOOP_DETECTED = "AGENT_LOOP_DETECTED"

    # Internal
    INTERNAL_ERROR = "INTERNAL_ERROR"


# ============================================
# MAZE MODELS
# ============================================


class MazeCell(BaseModel):
    """Individual maze cell with wall information"""

    x: int = Field(ge=0, description="X coordinate")
    y: int = Field(ge=0, description="Y coordinate")
    walls: Dict[str, bool] = Field(
        description="Walls around cell: top, right, bottom, left"
    )

    @field_validator("walls")
    @classmethod
    def validate_walls(cls, v):
        required_keys = {"top", "right", "bottom", "left"}
        if not all(k in v for k in required_keys):
            raise ValueError(f"walls must contain: {required_keys}")
        return v


class MazePosition(BaseModel):
    """Position in the maze"""

    x: int = Field(ge=0, description="X coordinate")
    y: int = Field(ge=0, description="Y coordinate")


class MazeWallData(BaseModel):
    """Wall data for maze generation"""

    key: str = Field(description="Wall key in format 'x1,y1-x2,y2'")


class MazeModel(BaseModel):
    """Complete maze structure"""

    size: int = Field(ge=3, le=50, description="Maze grid size (NxN)")
    start: MazePosition = Field(description="Start position")
    end: MazePosition = Field(description="End position")
    walls: List[str] = Field(default_factory=list, description="List of wall keys")

    @field_validator("start", "end")
    @classmethod
    def validate_position(cls, v, info):
        # Will be validated against size in model_validate
        return v


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================


class MazeSolveRequest(BaseModel):
    """Request to solve a maze"""

    maze: MazeModel = Field(description="The maze to solve")
    model: str = Field(
        default="openai/gpt-4o",
        description="OpenAI model to use (or OpenRouter format)",
    )
    api_key: Optional[str] = Field(
        default=None, description="API key (can also use OPENAI_API_KEY env var)"
    )
    max_iterations: int = Field(
        default=500, ge=10, le=2000, description="Maximum agent iterations"
    )
    temperature: float = Field(
        default=0.3, ge=0.0, le=2.0, description="Model temperature"
    )

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v):
        import os

        if not v:
            v = os.getenv("OPENAI_API_KEY")
        if not v:
            raise ValueError(
                "API key is required (provide api_key or set OPENAI_API_KEY)"
            )
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "maze": {
                    "size": 10,
                    "start": {"x": 0, "y": 0},
                    "end": {"x": 9, "y": 9},
                    "walls": ["0,0-1,0", "0,0-0,1"],
                },
                "model": "openai/gpt-4o",
                "max_iterations": 500,
            }
        }


class MazeSolveResponse(BaseModel):
    """Response for maze solving (streaming)"""

    # This is handled via SSE, so minimal response model
    pass


# ============================================
# EVENT MODELS
# ============================================


class AgentEvent(BaseModel):
    """Event from the agent during solving"""

    event: EventType = Field(description="Type of event")
    data: Dict[str, Any] = Field(description="Event data")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Event timestamp"
    )

    def to_sse(self) -> str:
        """Convert to SSE format"""
        import json

        return f"data: {json.dumps(self.model_dump())}\n\n"


class ToolCallEvent(BaseModel):
    """Tool call event data"""

    tool_name: str = Field(description="Name of tool called")
    tool_call_id: str = Field(description="Unique ID for this tool call")
    position: MazePosition = Field(description="Current agent position")
    step_count: int = Field(description="Total steps taken")


class ToolResultEvent(BaseModel):
    """Tool result event data"""

    tool_name: str = Field(description="Name of executed tool")
    tool_call_id: str = Field(description="ID of the tool call")
    result: Dict[str, Any] = Field(description="Tool execution result")
    success: bool = Field(description="Whether tool succeeded")
    position: MazePosition = Field(description="Position after tool execution")


class PositionUpdateEvent(BaseModel):
    """Position update event"""

    position: MazePosition = Field(description="New position")
    direction: Optional[str] = Field(default=None, description="Direction moved")
    step_count: int = Field(description="Total steps taken")
    path: List[Dict[str, int]] = Field(description="Full path taken")
    is_complete: bool = Field(description="Whether maze is solved")


class LogEventData(BaseModel):
    """Log event data"""

    level: Literal["DEBUG", "INFO", "WARN", "ERROR"] = Field(description="Log level")
    category: str = Field(description="Log category")
    code: str = Field(description="Error/code identifier")
    message: str = Field(description="Log message")
    data: Dict[str, Any] = Field(default_factory=dict, description="Additional data")


class ErrorEventData(BaseModel):
    """Error event data"""

    code: ErrorCode = Field(description="Error code")
    category: ErrorCategory = Field(description="Error category")
    message: str = Field(description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Error details")


class CompleteEventData(BaseModel):
    """Completion event data"""

    success: bool = Field(description="Whether maze was solved")
    path: List[Dict[str, int]] = Field(description="Solution path")
    steps: int = Field(description="Total steps taken")
    logs: List[Dict[str, Any]] = Field(description="All logs from solving")


class PromptEventData(BaseModel):
    """Full prompt sent to LLM - for observability"""

    system_prompt: str = Field(description="System prompt content")
    user_prompt: str = Field(description="User prompt content")
    tools: List[Dict[str, Any]] = Field(description="Tools definition")
    model: str = Field(description="Model being used")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When prompt was sent"
    )


# ============================================
# ERROR MODEL
# ============================================


class MazeAgentError(Exception):
    """Custom exception for maze agent errors"""

    def __init__(
        self,
        code: ErrorCode,
        category: ErrorCategory,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.code = code
        self.category = category
        self.message = message
        self.details = details or {}
        super().__init__(message)


# ============================================
# LOGGING MODELS
# ============================================


class LogEntry(BaseModel):
    """Structured log entry"""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    level: Literal["DEBUG", "INFO", "WARN", "ERROR"] = "INFO"
    category: str
    code: str
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)

    def __str__(self):
        return f"[{self.timestamp.isoformat()}] {self.level}: {self.category}/{self.code} - {self.message}"


# ============================================
# RESPONSE MODELS
# ============================================


class ErrorResponse(BaseModel):
    """Standard error response"""

    error: ErrorEventData
    request_id: Optional[str] = Field(
        default=None, description="Request ID for tracing"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    service: str
    version: str
    timestamp: datetime
    openai_configured: bool = False


# ============================================
# INSPECTOR (Output Validation)
# ============================================


class AgentOutputInspector:
    """
    Inspects and validates agent outputs
    Following Open/Closed Principle - extensible for new validation rules
    """

    @staticmethod
    def validate_tool_call(response: Dict[str, Any]) -> bool:
        """Validate that response contains valid tool call"""
        if not response.get("tool_calls"):
            return True  # Text-only responses are valid

        for tool_call in response["tool_calls"]:
            if not tool_call.get("function"):
                return False
            if not tool_call["function"].get("name"):
                return False
        return True

    @staticmethod
    def validate_position(position: Dict[str, int], maze_size: int) -> bool:
        """Validate position is within maze bounds"""
        x = position.get("x", -1)
        y = position.get("y", -1)
        return 0 <= x < maze_size and 0 <= y < maze_size

    @staticmethod
    def detect_loop(path: List[Dict[str, int]], threshold: int = 3) -> bool:
        """Detect if agent is stuck in a loop"""
        if len(path) < threshold * 2:
            return False

        recent = [f"{p.get('x', -1)},{p.get('y', -1)}" for p in path[-threshold * 2 :]]

        # Check for repeating patterns
        for i in range(len(recent) - threshold):
            if recent[i : i + threshold] == recent[i + threshold : i + 2 * threshold]:
                return True
        return False

    @staticmethod
    def validate_path(path: List[Dict[str, int]], maze: MazeModel) -> bool:
        """Validate that path is valid (adjacent moves only)"""
        if not path:
            return False

        for i in range(1, len(path)):
            prev = path[i - 1]
            curr = path[i]
            dx = abs(curr.get("x", 0) - prev.get("x", 0))
            dy = abs(curr.get("y", 0) - prev.get("y", 0))
            if dx + dy != 1:  # Must be exactly one step
                return False
        return True
