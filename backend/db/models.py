from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Numeric,
    JSON,
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


def generate_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    clerk_id = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    mazes = relationship("Maze", back_populates="user", cascade="all, delete-orphan")
    attempts = relationship(
        "Attempt", back_populates="user", cascade="all, delete-orphan"
    )
    api_calls = relationship(
        "ApiCall", back_populates="user", cascade="all, delete-orphan"
    )


class Maze(Base):
    __tablename__ = "mazes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=True)
    size = Column(Integer, nullable=False)
    start_x = Column(Integer, nullable=False)
    start_y = Column(Integer, nullable=False)
    end_x = Column(Integer, nullable=False)
    end_y = Column(Integer, nullable=False)
    walls = Column(Text, nullable=False)
    is_challenge = Column(Boolean, default=False)
    challenge_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="mazes")
    attempts = relationship(
        "Attempt", back_populates="maze", cascade="all, delete-orphan"
    )


class Attempt(Base):
    __tablename__ = "attempts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    maze_id = Column(String(36), ForeignKey("mazes.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    model = Column(String(255), nullable=False, index=True)
    success = Column(Boolean, default=False)
    steps = Column(Integer, default=0)
    path = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    medal = Column(String(10), nullable=True)
    challenge_id = Column(String(50), nullable=True, index=True)

    maze = relationship("Maze", back_populates="attempts")
    user = relationship("User", back_populates="attempts")
    events = relationship(
        "Event", back_populates="attempt", cascade="all, delete-orphan"
    )
    api_calls = relationship(
        "ApiCall", back_populates="attempt", cascade="all, delete-orphan"
    )


class Event(Base):
    __tablename__ = "events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    attempt_id = Column(
        String(36), ForeignKey("attempts.id"), nullable=False, index=True
    )
    event_type = Column(String(50), nullable=False, index=True)
    event_data = Column(JSON, nullable=True)
    position_x = Column(Integer, nullable=True)
    position_y = Column(Integer, nullable=True)
    step_number = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    attempt = relationship("Attempt", back_populates="events")


class ApiCall(Base):
    __tablename__ = "api_calls"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    attempt_id = Column(
        String(36), ForeignKey("attempts.id"), nullable=True, index=True
    )
    model = Column(String(255), nullable=False)
    provider = Column(String(100), nullable=True)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost_usd = Column(Numeric(10, 8), default=0)
    latency_ms = Column(Integer, nullable=True)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    request_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="api_calls")
    attempt = relationship("Attempt", back_populates="api_calls")


class Challenge(Base):
    __tablename__ = "challenges"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    model = Column(String(255), nullable=False)
    time_limit_minutes = Column(Integer, nullable=False)
    grid_size = Column(Integer, nullable=False)
    difficulty = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class MazeBenchEntry(Base):
    __tablename__ = "mazebench_entries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    model = Column(String(255), nullable=False, index=True)
    total_solves = Column(Integer, default=0)
    successful_solves = Column(Integer, default=0)
    total_steps = Column(Integer, default=0)
    total_duration_ms = Column(Integer, default=0)
    score = Column(Numeric(10, 6), default=0)
    gold_count = Column(Integer, default=0)
    silver_count = Column(Integer, default=0)
    bronze_count = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = ({"extend_existing": True},)


class MazeStats(Base):
    __tablename__ = "maze_stats"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    maze_id = Column(
        String(36), ForeignKey("mazes.id"), nullable=False, unique=True, index=True
    )
    best_time_ms = Column(Integer, nullable=True)
    median_time_ms = Column(Integer, nullable=True)
    total_attempts = Column(Integer, default=0)
    successful_attempts = Column(Integer, default=0)
    gold_threshold_ms = Column(Integer, nullable=True)
    silver_threshold_ms = Column(Integer, nullable=True)
    bronze_threshold_ms = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
