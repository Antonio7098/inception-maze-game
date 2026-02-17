"""
Structured Logging Module
Provides structured logging with error taxonomy
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass, field, asdict
from pathlib import Path


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class ErrorTaxonomy:
    """Error taxonomy following SOLID principles"""

    # Authentication errors
    AUTH = {
        "INVALID_API_KEY": "AUTH_INVALID_API_KEY",
        "MISSING_API_KEY": "AUTH_MISSING_API_KEY",
        "RATE_LIMITED": "AUTH_RATE_LIMITED",
        "INSUFFICIENT_CREDITS": "AUTH_INSUFFICIENT_CREDITS",
    }

    # Network errors
    NETWORK = {
        "CONNECTION_FAILED": "NETWORK_CONNECTION_FAILED",
        "TIMEOUT": "NETWORK_TIMEOUT",
        "REQUEST_FAILED": "NETWORK_REQUEST_FAILED",
    }

    # Validation errors
    VALIDATION = {
        "INVALID_MAZE": "VALIDATION_INVALID_MAZE",
        "INVALID_POSITION": "VALIDATION_INVALID_POSITION",
        "SCHEMA_MISMATCH": "VALIDATION_SCHEMA_MISMATCH",
    }

    # Maze errors
    MAZE = {
        "NO_PATH": "MAZE_NO_PATH",
        "START_BLOCKED": "MAZE_START_BLOCKED",
        "END_BLOCKED": "MAZE_END_BLOCKED",
    }

    # Agent errors
    AGENT = {
        "MAX_STEPS_REACHED": "AGENT_MAX_STEPS_REACHED",
        "INVALID_TOOL_CALL": "AGENT_INVALID_TOOL_CALL",
        "TOOL_EXECUTION_FAILED": "AGENT_TOOL_EXECUTION_FAILED",
        "LOOP_DETECTED": "AGENT_LOOP_DETECTED",
    }

    # Internal errors
    INTERNAL = {"INTERNAL_ERROR": "INTERNAL_ERROR"}

    @classmethod
    def get_category(cls, code: str) -> str:
        """Get category from error code"""
        code = code.split("_")[0]
        return (
            code
            if code in ["AUTH", "NETWORK", "VALIDATION", "MAZE", "AGENT", "INTERNAL"]
            else "INTERNAL"
        )


@dataclass
class LogEntry:
    """Structured log entry"""

    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    level: str = "INFO"
    category: str = "AGENT"
    code: str = "LOG"
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    request_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class StructuredLogger:
    """
    Structured logger with event streaming support
    Following Single Responsibility Principle
    """

    def __init__(
        self,
        name: str,
        log_file: Optional[str] = None,
        on_log: Optional[callable] = None,
    ):
        self.name = name
        self.logger = logging.getLogger(name)
        self.log_entries: List[LogEntry] = []
        self.on_log = on_log

        # File handler if specified
        if log_file:
            handler = logging.FileHandler(log_file)
            handler.setFormatter(
                logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s")
            )
            self.logger.addHandler(handler)

    def _emit(
        self,
        level: str,
        category: str,
        code: str,
        message: str,
        data: Dict[str, Any] = None,
    ):
        """Emit a log entry"""
        entry = LogEntry(
            level=level, category=category, code=code, message=message, data=data or {}
        )

        self.log_entries.append(entry)

        # Call callback if provided (for SSE streaming)
        if self.on_log:
            self.on_log(entry.to_dict())

        # Also log to standard logger
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(f"[{category}] {code}: {message}", extra={"data": data or {}})

    def debug(
        self, category: str, code: str, message: str, data: Dict[str, Any] = None
    ):
        self._emit("DEBUG", category, code, message, data)

    def info(self, category: str, code: str, message: str, data: Dict[str, Any] = None):
        self._emit("INFO", category, code, message, data)

    def warn(self, category: str, code: str, message: str, data: Dict[str, Any] = None):
        self._emit("WARN", category, code, message, data)

    def error(
        self, category: str, code: str, message: str, data: Dict[str, Any] = None
    ):
        self._emit("ERROR", category, code, message, data)

    def get_logs(self) -> List[Dict[str, Any]]:
        """Get all log entries"""
        return [entry.to_dict() for entry in self.log_entries]

    def clear(self):
        """Clear log entries"""
        self.log_entries = []

    def get_error_count(self) -> int:
        return sum(1 for e in self.log_entries if e.level == "ERROR")

    def get_warn_count(self) -> int:
        return sum(1 for e in self.log_entries if e.level == "WARN")


class EventLogger:
    """
    Event logger for SSE streaming
    """

    def __init__(self, on_event: Optional[callable] = None):
        self.on_event = on_event
        self.events: List[Dict[str, Any]] = []

    def emit(self, event_type: str, data: Dict[str, Any], level: str = "INFO"):
        """Emit an event"""
        event = {
            "event": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
        }

        self.events.append(event)

        if self.on_event:
            self.on_event(event)

    def init(self, message: str, **kwargs):
        self.emit("init", {"message": message, **kwargs})

    def tool_call(self, tool_name: str, position: Dict, step: int):
        self.emit(
            "tool_call",
            {"tool_name": tool_name, "position": position, "step_count": step},
        )

    def tool_result(self, tool_name: str, result: Dict, success: bool):
        self.emit(
            "tool_result",
            {"tool_name": tool_name, "result": result, "success": success},
        )

    def position(self, position: Dict, step: int, path: List, is_complete: bool):
        self.emit(
            "position_update",
            {
                "position": position,
                "step_count": step,
                "path": path,
                "is_complete": is_complete,
            },
        )

    def log(
        self, level: str, category: str, code: str, message: str, data: Dict = None
    ):
        self.emit(
            "log",
            {
                "level": level,
                "category": category,
                "code": code,
                "message": message,
                "data": data or {},
            },
        )

    def error(self, code: str, message: str, details: Dict = None):
        self.emit(
            "error",
            {"code": code, "message": message, "details": details or {}},
            level="ERROR",
        )

    def complete(self, success: bool, path: List, steps: int):
        self.emit("complete", {"success": success, "path": path, "steps": steps})

    def prompt(self, system_prompt: str, user_prompt: str, tools: List, model: str):
        self.emit(
            "prompt",
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "tools": tools,
                "model": model,
            },
        )

    def get_events(self) -> List[Dict[str, Any]]:
        return self.events
