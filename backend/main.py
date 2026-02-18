import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import os
import json
import asyncio
import httpx
import logging
from decimal import Decimal
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from openai import OpenAI

from db import (
    get_async_session,
    init_db,
    close_db,
    User,
    Maze,
    Attempt,
    Event,
    ApiCall,
    MazeBenchEntry,
    MazeStats,
)
from services.openrouter import get_tool_capable_models
from services.challenges import get_challenges, get_challenge_by_id
from services.leaderboard import (
    update_maze_stats,
    assign_medal_to_attempt,
    update_mazebench_entry,
    get_mazebench_leaderboard,
    get_challenge_solutions,
    get_challenge_best_times,
)

load_dotenv = __import__("dotenv").load_dotenv
load_dotenv()

VERSION = "0.1.0"

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(message)s", level=logging.INFO
)
logger = logging.getLogger("maze_app")

app = FastAPI(title="Maze Game API", version=VERSION)
security = HTTPBearer()

OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "")
CLERK_API_URL = "https://api.clerk.com/v1"


async def get_user_private_metadata(clerk_id: str) -> dict:
    """Fetch user's private metadata from Clerk"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{CLERK_API_URL}/users/{clerk_id}/metadata",
            headers={"Authorization": f"Bearer {CLERK_SECRET_KEY}"},
        )
        response.raise_for_status()
        return response.json()


async def update_user_private_metadata(clerk_id: str, metadata: dict) -> dict:
    """Update user's private metadata in Clerk"""
    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{CLERK_API_URL}/users/{clerk_id}/metadata",
            headers={
                "Authorization": f"Bearer {CLERK_SECRET_KEY}",
                "Content-Type": "application/json",
            },
            json={"private_metadata": metadata},
        )
        response.raise_for_status()
        return response.json()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await init_db()


@app.on_event("shutdown")
async def shutdown():
    await close_db()


@app.get("/api/version")
async def get_version():
    """Get API version"""
    return {"version": VERSION}


# Pydantic Models
class MazePosition(BaseModel):
    x: int
    y: int


class MazeCreate(BaseModel):
    name: Optional[str] = None
    size: int = Field(ge=5, le=50)
    start: MazePosition
    end: MazePosition
    walls: List[str]


class AttemptCreate(BaseModel):
    maze_id: str
    model: str
    max_iterations: int = 500


class ApiKeyUpdate(BaseModel):
    api_key: str


# Auth Helpers
async def verify_clerk_token(token: str) -> Dict[str, Any]:
    import jwt
    from jwt import PyJWKClient

    jwk_client = PyJWKClient("https://api.clerk.com/v1/jwks")
    signing_key = jwk_client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token, signing_key.key, algorithms=["RS256"], options={"verify_aud": False}
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    payload = await verify_clerk_token(credentials.credentials)
    clerk_id = payload.get("sub")
    email = payload.get("email", "")

    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()

    if not user:
        user = User(clerk_id=clerk_id, email=email)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    try:
        metadata = await get_user_private_metadata(clerk_id)
        api_key = metadata.get("private_metadata", {}).get("openrouter_api_key")
    except Exception as e:
        logger.warning(f"Failed to fetch private metadata: {e}")
        api_key = None

    return {
        "id": user.id,
        "clerk_id": clerk_id,
        "email": email,
        "api_key": api_key,
        "db": db,
    }


# Auth Routes
@app.get("/api/auth/me")
async def get_me(user: Dict = Depends(get_current_user)):
    return {
        "id": user["id"],
        "email": user["email"],
        "has_api_key": bool(user.get("api_key")),
    }


@app.post("/api/auth/api-key")
async def update_api_key(data: ApiKeyUpdate, user: Dict = Depends(get_current_user)):
    clerk_id = user["clerk_id"]
    try:
        metadata = await get_user_private_metadata(clerk_id)
        private_metadata = metadata.get("private_metadata", {})
        private_metadata["openrouter_api_key"] = data.api_key
        await update_user_private_metadata(clerk_id, private_metadata)
    except Exception as e:
        logger.error(f"Failed to update private metadata: {e}")
        raise HTTPException(status_code=500, detail="Failed to save API key")
    return {"success": True}


# Models Routes
@app.get("/api/models")
async def list_models():
    try:
        models = await get_tool_capable_models()
        return {"models": models}
    except Exception as e:
        logger.error(f"Failed to fetch models: {e}")
        return {
            "models": [
                {
                    "id": "meta-llama/llama-3.3-8b-instruct:free",
                    "name": "Llama 3.3 8B",
                    "provider": "meta-llama",
                    "is_free": True,
                }
            ]
        }


# Challenges Routes
@app.get("/api/challenges")
async def list_challenges():
    return {"challenges": get_challenges()}


@app.get("/api/challenges/{challenge_id}")
async def get_challenge_endpoint(challenge_id: str):
    challenge = get_challenge_by_id(challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    return challenge


# Mazes Routes
@app.get("/api/mazes")
async def list_mazes(user: Dict = Depends(get_current_user)):
    db = user["db"]
    result = await db.execute(
        select(Maze).where(Maze.user_id == user["id"]).order_by(desc(Maze.created_at))
    )
    mazes = result.scalars().all()
    return {
        "mazes": [
            {
                "id": m.id,
                "name": m.name,
                "size": m.size,
                "start": {"x": m.start_x, "y": m.start_y},
                "end": {"x": m.end_x, "y": m.end_y},
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in mazes
        ]
    }


@app.post("/api/mazes")
async def create_maze(data: MazeCreate, user: Dict = Depends(get_current_user)):
    db = user["db"]
    maze = Maze(
        user_id=user["id"],
        name=data.name or f"Maze {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        size=data.size,
        start_x=data.start.x,
        start_y=data.start.y,
        end_x=data.end.x,
        end_y=data.end.y,
        walls=json.dumps(data.walls),
    )
    db.add(maze)
    await db.commit()
    await db.refresh(maze)
    return {"id": maze.id, "name": maze.name}


@app.get("/api/mazes/{maze_id}")
async def get_maze(maze_id: str, user: Dict = Depends(get_current_user)):
    db = user["db"]
    result = await db.execute(
        select(Maze).where(Maze.id == maze_id, Maze.user_id == user["id"])
    )
    maze = result.scalar_one_or_none()
    if not maze:
        raise HTTPException(status_code=404, detail="Maze not found")
    return {
        "id": maze.id,
        "name": maze.name,
        "size": maze.size,
        "start": {"x": maze.start_x, "y": maze.start_y},
        "end": {"x": maze.end_x, "y": maze.end_y},
        "walls": json.loads(maze.walls),
        "created_at": maze.created_at.isoformat() if maze.created_at else None,
    }


@app.delete("/api/mazes/{maze_id}")
async def delete_maze(maze_id: str, user: Dict = Depends(get_current_user)):
    db = user["db"]
    result = await db.execute(
        select(Maze).where(Maze.id == maze_id, Maze.user_id == user["id"])
    )
    maze = result.scalar_one_or_none()
    if not maze:
        raise HTTPException(status_code=404, detail="Maze not found")
    await db.delete(maze)
    await db.commit()
    return {"success": True}


# Attempts Routes
@app.get("/api/mazes/{maze_id}/attempts")
async def list_attempts(maze_id: str, user: Dict = Depends(get_current_user)):
    db = user["db"]
    result = await db.execute(
        select(Attempt)
        .where(Attempt.maze_id == maze_id)
        .order_by(desc(Attempt.started_at))
    )
    attempts = result.scalars().all()
    return {
        "attempts": [
            {
                "id": a.id,
                "model": a.model,
                "success": a.success,
                "steps": a.steps,
                "duration_ms": a.duration_ms,
                "medal": a.medal,
                "started_at": a.started_at.isoformat() if a.started_at else None,
            }
            for a in attempts
        ]
    }


@app.get("/api/attempts/{attempt_id}")
async def get_attempt(attempt_id: str, user: Dict = Depends(get_current_user)):
    db = user["db"]
    result = await db.execute(select(Attempt).where(Attempt.id == attempt_id))
    attempt = result.scalar_one_or_none()
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")

    events_result = await db.execute(
        select(Event).where(Event.attempt_id == attempt_id).order_by(Event.created_at)
    )
    events = events_result.scalars().all()

    return {
        "id": attempt.id,
        "maze_id": attempt.maze_id,
        "model": attempt.model,
        "success": attempt.success,
        "steps": attempt.steps,
        "path": json.loads(attempt.path) if attempt.path else [],
        "duration_ms": attempt.duration_ms,
        "started_at": attempt.started_at.isoformat() if attempt.started_at else None,
        "events": [
            {
                "type": e.event_type,
                "data": e.event_data,
                "position": {"x": e.position_x, "y": e.position_y}
                if e.position_x is not None
                else None,
                "step": e.step_number,
            }
            for e in events
        ],
    }


# Maze Solving Tools
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_position",
            "description": "Get current position",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "move_up",
            "description": "Move up",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "move_down",
            "description": "Move down",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "move_left",
            "description": "Move left",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "move_right",
            "description": "Move right",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_moves",
            "description": "Get available moves",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_goal",
            "description": "Check if at goal",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


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
            right = "|" if f"{x},{y}-{x + 1},{y}" in walls_set or x == size - 1 else " "
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
    return "\n".join(lines)


def has_wall_between(x1, y1, x2, y2, walls_set):
    if x1 == x2:
        max_y = max(y1, y2)
        wall_key = f"{x1},{max_y}-{x1 + 1},{max_y}"
        return wall_key in walls_set
    else:
        max_x = max(x1, x2)
        wall_key = f"{max_x},{y1}-{max_x},{y1 + 1}"
        return wall_key in walls_set


def execute_tool(tool_name, pos, maze_size, walls_set, end, steps):
    x, y = pos["x"], pos["y"]

    if tool_name == "get_current_position":
        return {"position": pos, "steps": steps}

    elif tool_name == "get_available_moves":
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

    elif tool_name == "check_goal":
        return {
            "is_complete": x == end["x"] and y == end["y"],
            "position": pos,
            "steps": steps,
        }

    elif tool_name.startswith("move_"):
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
        return {
            "success": True,
            "position": new_pos,
            "is_complete": at_end,
            "steps": steps,
            "message": f"Moved {direction}",
        }

    return {"error": "Unknown tool"}


def format_sse(data):
    return f"data: {json.dumps(data)}\n\n"


@app.post("/api/attempts")
async def create_attempt(data: AttemptCreate, user: Dict = Depends(get_current_user)):
    db = user["db"]

    result = await db.execute(select(Maze).where(Maze.id == data.maze_id))
    maze = result.scalar_one_or_none()
    if not maze:
        raise HTTPException(status_code=404, detail="Maze not found")

    api_key = user.get("api_key") or os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="No API key configured")

    attempt = Attempt(
        maze_id=data.maze_id,
        user_id=user["id"],
        model=data.model,
        started_at=datetime.utcnow(),
        challenge_id=maze.challenge_id,
    )
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)

    walls = json.loads(maze.walls)
    walls_set = set(walls)
    start = {"x": maze.start_x, "y": maze.start_y}
    end = {"x": maze.end_x, "y": maze.end_y}

    async def event_generator():
        nonlocal attempt
        client = OpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL, timeout=120.0)

        position = dict(start)
        path = [dict(position)]
        steps = 0
        is_complete = False

        ascii_maze = get_ascii_maze(maze.size, walls, start, end)
        system_prompt = f"You are a maze-solving agent. Navigate from START(S) to END(E).\n\nMAZE:\n{ascii_maze}\n\nStart: ({start['x']}, {start['y']})\nEnd: ({end['x']}, {end['y']})\n\nUse tools to move. Goal: reach End."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Solve this maze!"},
        ]

        yield format_sse({"event": "init", "data": {"attempt_id": attempt.id}})

        total_tokens = 0
        start_time = datetime.utcnow()

        for iteration in range(data.max_iterations):
            if is_complete:
                break

            try:
                response = client.chat.completions.create(
                    model=data.model,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    temperature=0.3,
                )

                total_tokens += response.usage.total_tokens if response.usage else 0
                msg = response.choices[0].message

                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        tool_name = tc.function.name
                        result = execute_tool(
                            tool_name, position, maze.size, walls_set, end, steps
                        )

                        event = Event(
                            attempt_id=attempt.id,
                            event_type="tool_call",
                            event_data={"tool": tool_name, "result": result},
                            position_x=position.get("x"),
                            position_y=position.get("y"),
                            step_number=steps,
                        )
                        db.add(event)

                        yield format_sse(
                            {
                                "event": "tool_call",
                                "data": {
                                    "tool": tool_name,
                                    "result": result,
                                    "position": position,
                                },
                            }
                        )

                        if "position" in result:
                            position = result["position"]
                            if position not in path:
                                path.append(dict(position))

                        if "is_complete" in result:
                            is_complete = result["is_complete"]

                        steps = result.get("steps", steps)

                        messages.append(
                            {
                                "role": "assistant",
                                "content": msg.content,
                                "tool_calls": [
                                    {
                                        "id": tc.id,
                                        "type": "function",
                                        "function": {
                                            "name": tool_name,
                                            "arguments": tc.function.arguments,
                                        },
                                    }
                                ],
                            }
                        )
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "content": json.dumps(result),
                            }
                        )

                yield format_sse(
                    {
                        "event": "position_update",
                        "data": {
                            "position": position,
                            "path": path,
                            "step": steps,
                            "complete": is_complete,
                        },
                    }
                )
                await asyncio.sleep(0.05)

            except Exception as e:
                yield format_sse({"event": "error", "data": {"message": str(e)}})
                break

        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        attempt.success = is_complete
        attempt.steps = steps
        attempt.path = json.dumps(path)
        attempt.duration_ms = duration_ms
        attempt.completed_at = end_time
        await db.commit()

        if is_complete:
            await update_maze_stats(db, data.maze_id)
            await assign_medal_to_attempt(db, attempt)
            await update_mazebench_entry(db, data.model)

        api_call = ApiCall(
            user_id=user["id"],
            attempt_id=attempt.id,
            model=data.model,
            total_tokens=total_tokens,
            cost_usd=Decimal(str(total_tokens * 0.00001)),
            latency_ms=duration_ms,
            success=True,
        )
        db.add(api_call)
        await db.commit()

        yield format_sse(
            {
                "event": "complete",
                "data": {
                    "success": is_complete,
                    "path": path,
                    "steps": steps,
                    "duration_ms": duration_ms,
                },
            }
        )

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# Monitoring Routes
@app.get("/api/monitoring/api-calls")
async def list_api_calls(period: str = "all", user: Dict = Depends(get_current_user)):
    db = user["db"]

    now = datetime.utcnow()
    if period == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)
    else:
        start_date = datetime(2020, 1, 1)

    result = await db.execute(
        select(ApiCall)
        .where(ApiCall.user_id == user["id"], ApiCall.created_at >= start_date)
        .order_by(desc(ApiCall.created_at))
    )
    calls = result.scalars().all()

    return {
        "calls": [
            {
                "id": c.id,
                "model": c.model,
                "total_tokens": c.total_tokens,
                "cost_usd": float(c.cost_usd) if c.cost_usd else 0,
                "latency_ms": c.latency_ms,
                "success": c.success,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "attempt_id": c.attempt_id,
            }
            for c in calls
        ],
        "total_cost": sum(float(c.cost_usd or 0) for c in calls),
        "total_tokens": sum(c.total_tokens or 0 for c in calls),
    }


@app.get("/api/monitoring/stats")
async def get_stats(user: Dict = Depends(get_current_user)):
    db = user["db"]

    result = await db.execute(select(ApiCall).where(ApiCall.user_id == user["id"]))
    all_calls = result.scalars().all()

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = datetime.utcnow() - timedelta(days=7)
    month_ago = datetime.utcnow() - timedelta(days=30)

    return {
        "total_calls": len(all_calls),
        "total_cost": sum(float(c.cost_usd or 0) for c in all_calls),
        "total_tokens": sum(c.total_tokens or 0 for c in all_calls),
        "today_calls": len([c for c in all_calls if c.created_at >= today]),
        "today_cost": sum(
            float(c.cost_usd or 0) for c in all_calls if c.created_at >= today
        ),
        "week_calls": len([c for c in all_calls if c.created_at >= week_ago]),
        "week_cost": sum(
            float(c.cost_usd or 0) for c in all_calls if c.created_at >= week_ago
        ),
        "month_calls": len([c for c in all_calls if c.created_at >= month_ago]),
        "month_cost": sum(
            float(c.cost_usd or 0) for c in all_calls if c.created_at >= month_ago
        ),
    }


@app.get("/api/mazebench")
async def get_mazebench(limit: int = 50, db: AsyncSession = Depends(get_async_session)):
    leaderboard = await get_mazebench_leaderboard(db, limit)
    return {"leaderboard": leaderboard}


@app.get("/api/challenges/{challenge_id}/solutions")
async def get_challenge_solutions_endpoint(
    challenge_id: str, limit: int = 50, db: AsyncSession = Depends(get_async_session)
):
    solutions = await get_challenge_solutions(db, challenge_id, limit)
    return {"solutions": solutions, "challenge_id": challenge_id}


@app.get("/api/challenges/stats")
async def get_challenges_stats(db: AsyncSession = Depends(get_async_session)):
    best_times = await get_challenge_best_times(db)
    return {"stats": best_times}


@app.get("/api/mazes/{maze_id}/stats")
async def get_maze_stats_endpoint(maze_id: str, user: Dict = Depends(get_current_user)):
    db = user["db"]
    result = await db.execute(select(MazeStats).where(MazeStats.maze_id == maze_id))
    stats = result.scalar_one_or_none()

    if not stats:
        return {"stats": None}

    return {
        "stats": {
            "best_time_ms": stats.best_time_ms,
            "median_time_ms": stats.median_time_ms,
            "total_attempts": stats.total_attempts,
            "successful_attempts": stats.successful_attempts,
            "gold_threshold_ms": stats.gold_threshold_ms,
            "silver_threshold_ms": stats.silver_threshold_ms,
            "bronze_threshold_ms": stats.bronze_threshold_ms,
        }
    }
