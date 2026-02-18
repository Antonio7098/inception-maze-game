import math
from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import datetime
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from db import Attempt, Maze, MazeBenchEntry, MazeStats, User


GOLD_THRESHOLD = 0.10
SILVER_THRESHOLD = 0.15
BRONZE_THRESHOLD = 0.20
MIN_MAZES_FOR_RANKING = 1


def calculate_medal(duration_ms: int, best_time_ms: int) -> Optional[str]:
    if not best_time_ms or not duration_ms:
        return None

    ratio = duration_ms / best_time_ms

    if ratio <= (1 + GOLD_THRESHOLD):
        return "gold"
    elif ratio <= (1 + SILVER_THRESHOLD):
        return "silver"
    elif ratio <= (1 + BRONZE_THRESHOLD):
        return "bronze"
    return None


async def update_maze_stats(db: AsyncSession, maze_id: str) -> Optional[MazeStats]:
    result = await db.execute(
        select(Attempt.duration_ms)
        .where(
            Attempt.maze_id == maze_id,
            Attempt.success == True,
            Attempt.duration_ms.isnot(None),
        )
        .order_by(Attempt.duration_ms)
    )
    times = [r[0] for r in result.fetchall()]

    if not times:
        return None

    best_time = min(times)
    median_time = times[len(times) // 2] if times else None

    gold_threshold = int(best_time * (1 + GOLD_THRESHOLD))
    silver_threshold = int(best_time * (1 + SILVER_THRESHOLD))
    bronze_threshold = int(best_time * (1 + BRONZE_THRESHOLD))

    total_result = await db.execute(
        select(func.count()).where(Attempt.maze_id == maze_id)
    )
    total_attempts = total_result.scalar() or 0

    success_result = await db.execute(
        select(func.count()).where(Attempt.maze_id == maze_id, Attempt.success == True)
    )
    successful_attempts = success_result.scalar() or 0

    stats_result = await db.execute(
        select(MazeStats).where(MazeStats.maze_id == maze_id)
    )
    stats = stats_result.scalar_one_or_none()

    if stats:
        stats.best_time_ms = best_time
        stats.median_time_ms = median_time
        stats.total_attempts = total_attempts
        stats.successful_attempts = successful_attempts
        stats.gold_threshold_ms = gold_threshold
        stats.silver_threshold_ms = silver_threshold
        stats.bronze_threshold_ms = bronze_threshold
        stats.updated_at = datetime.utcnow()
    else:
        stats = MazeStats(
            maze_id=maze_id,
            best_time_ms=best_time,
            median_time_ms=median_time,
            total_attempts=total_attempts,
            successful_attempts=successful_attempts,
            gold_threshold_ms=gold_threshold,
            silver_threshold_ms=silver_threshold,
            bronze_threshold_ms=bronze_threshold,
        )
        db.add(stats)

    await db.commit()
    await db.refresh(stats)
    return stats


async def assign_medal_to_attempt(db: AsyncSession, attempt: Attempt) -> Optional[str]:
    if not attempt.success or not attempt.duration_ms:
        return None

    stats_result = await db.execute(
        select(MazeStats).where(MazeStats.maze_id == attempt.maze_id)
    )
    stats = stats_result.scalar_one_or_none()

    if not stats or not stats.best_time_ms:
        stats = await update_maze_stats(db, attempt.maze_id)
        if not stats:
            return None

    medal = calculate_medal(attempt.duration_ms, stats.best_time_ms)
    attempt.medal = medal
    await db.commit()
    return medal


async def calculate_model_score(
    db: AsyncSession, model: str
) -> Optional[Dict[str, Any]]:
    result = await db.execute(
        select(
            Attempt.maze_id, Attempt.duration_ms, Attempt.success, Attempt.medal
        ).where(Attempt.model == model)
    )
    attempts = result.fetchall()

    if not attempts:
        return None

    successful_mazes = set()
    total_steps = 0
    total_duration = 0
    gold_count = 0
    silver_count = 0
    bronze_count = 0

    for maze_id, duration_ms, success, medal in attempts:
        if success and duration_ms:
            successful_mazes.add(maze_id)
            total_duration += duration_ms
        if medal == "gold":
            gold_count += 1
        elif medal == "silver":
            silver_count += 1
        elif medal == "bronze":
            bronze_count += 1

    if len(successful_mazes) < MIN_MAZES_FOR_RANKING:
        return None

    maze_scores = []
    for maze_id in successful_mazes:
        stats_result = await db.execute(
            select(MazeStats.median_time_ms).where(MazeStats.maze_id == maze_id)
        )
        median_time = stats_result.scalar_one_or_none()

        if not median_time:
            continue

        attempt_result = await db.execute(
            select(func.min(Attempt.duration_ms)).where(
                Attempt.model == model,
                Attempt.maze_id == maze_id,
                Attempt.success == True,
            )
        )
        best_attempt_time = attempt_result.scalar()

        if best_attempt_time and median_time > 0:
            score = median_time / best_attempt_time
            score = min(score, Decimal("1.0"))
            maze_scores.append(float(score))

    if not maze_scores:
        return None

    geometric_mean = math.exp(sum(math.log(s) for s in maze_scores) / len(maze_scores))

    return {
        "model": model,
        "total_solves": len(attempts),
        "successful_solves": len(successful_mazes),
        "total_duration_ms": total_duration,
        "score": round(geometric_mean, 6),
        "gold_count": gold_count,
        "silver_count": silver_count,
        "bronze_count": bronze_count,
    }


async def update_mazebench_entry(
    db: AsyncSession, model: str
) -> Optional[MazeBenchEntry]:
    data = await calculate_model_score(db, model)

    if not data:
        return None

    result = await db.execute(
        select(MazeBenchEntry).where(MazeBenchEntry.model == model)
    )
    entry = result.scalar_one_or_none()

    if entry:
        entry.total_solves = data["total_solves"]
        entry.successful_solves = data["successful_solves"]
        entry.total_duration_ms = data["total_duration_ms"]
        entry.score = Decimal(str(data["score"]))
        entry.gold_count = data["gold_count"]
        entry.silver_count = data["silver_count"]
        entry.bronze_count = data["bronze_count"]
        entry.updated_at = datetime.utcnow()
    else:
        entry = MazeBenchEntry(
            model=model,
            total_solves=data["total_solves"],
            successful_solves=data["successful_solves"],
            total_duration_ms=data["total_duration_ms"],
            score=Decimal(str(data["score"])),
            gold_count=data["gold_count"],
            silver_count=data["silver_count"],
            bronze_count=data["bronze_count"],
        )
        db.add(entry)

    await db.commit()
    await db.refresh(entry)
    return entry


async def get_mazebench_leaderboard(
    db: AsyncSession, limit: int = 50
) -> List[Dict[str, Any]]:
    result = await db.execute(
        select(MazeBenchEntry)
        .where(MazeBenchEntry.successful_solves >= MIN_MAZES_FOR_RANKING)
        .order_by(MazeBenchEntry.score.desc())
        .limit(limit)
    )
    entries = result.scalars().all()

    return [
        {
            "rank": idx + 1,
            "model": e.model,
            "score": float(e.score),
            "total_solves": e.total_solves,
            "successful_solves": e.successful_solves,
            "gold_count": e.gold_count,
            "silver_count": e.silver_count,
            "bronze_count": e.bronze_count,
            "updated_at": e.updated_at.isoformat() if e.updated_at else None,
        }
        for idx, e in enumerate(entries)
    ]


async def get_challenge_solutions(
    db: AsyncSession, challenge_id: str, limit: int = 50
) -> List[Dict[str, Any]]:
    result = await db.execute(
        select(Attempt, User.email)
        .join(User, Attempt.user_id == User.id)
        .where(Attempt.challenge_id == challenge_id, Attempt.success == True)
        .order_by(Attempt.duration_ms.asc())
        .limit(limit)
    )
    rows = result.fetchall()

    return [
        {
            "attempt_id": attempt.id,
            "model": attempt.model,
            "user_email": email.split("@")[0] + "@..." if email else "Anonymous",
            "steps": attempt.steps,
            "duration_ms": attempt.duration_ms,
            "medal": attempt.medal,
            "completed_at": attempt.completed_at.isoformat()
            if attempt.completed_at
            else None,
        }
        for attempt, email in rows
    ]


async def get_challenge_best_times(db: AsyncSession) -> Dict[str, Dict[str, Any]]:
    result = await db.execute(
        select(
            Attempt.challenge_id,
            func.min(Attempt.duration_ms).label("best_time"),
            func.count(Attempt.id).label("total_solves"),
        )
        .where(Attempt.challenge_id.isnot(None), Attempt.success == True)
        .group_by(Attempt.challenge_id)
    )

    return {
        row.challenge_id: {
            "best_time_ms": row.best_time,
            "total_solves": row.total_solves,
        }
        for row in result.fetchall()
    }
