"""
Database layer for Maestro AI.
Uses SQLAlchemy async with SQLite backend.
Tables: tasks, task_results, failed_tasks, logs
"""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import select, update
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./maestro.db")

# Automatically translate standard PostgreSQL URLs to use the asyncpg driver
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)



class Base(DeclarativeBase):
    pass


# ─── Models ───────────────────────────────────────────────────────────────────

class Task(Base):
    __tablename__ = "tasks"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_query = Column(Text, nullable=False)
    status = Column(String, default="pending")      # pending | running | completed | failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    subtask_count = Column(Integer, default=0)
    completed_subtasks = Column(Integer, default=0)


class TaskResult(Base):
    __tablename__ = "task_results"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, nullable=False)
    agent = Column(String, nullable=False)          # retriever | analyzer | writer | validator
    subtask_index = Column(Integer, default=0)
    result = Column(Text, nullable=True)
    success = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class FailedTask(Base):
    __tablename__ = "failed_tasks"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, nullable=False)
    agent = Column(String, nullable=False)
    instruction = Column(Text, nullable=False)
    error = Column(Text, nullable=True)
    retries = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class Log(Base):
    __tablename__ = "logs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, nullable=True)
    level = Column(String, default="INFO")          # INFO | WARNING | ERROR
    component = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ─── Init ─────────────────────────────────────────────────────────────────────

async def init_db():
    """Create all tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ─── CRUD Helpers ─────────────────────────────────────────────────────────────

async def create_task(query: str) -> str:
    """Insert a new task and return its ID."""
    task_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        task = Task(id=task_id, user_query=query, status="pending")
        session.add(task)
        await session.commit()
    return task_id


async def update_task_status(task_id: str, status: str, subtask_count: int = None):
    async with AsyncSessionLocal() as session:
        values = {"status": status, "updated_at": datetime.utcnow()}
        if subtask_count is not None:
            values["subtask_count"] = subtask_count
        await session.execute(update(Task).where(Task.id == task_id).values(**values))
        await session.commit()


async def increment_completed_subtasks(task_id: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if task:
            task.completed_subtasks += 1
            task.updated_at = datetime.utcnow()
            await session.commit()


async def get_task(task_id: str) -> Optional[dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            return None
        return {
            "id": task.id,
            "user_query": task.user_query,
            "status": task.status,
            "subtask_count": task.subtask_count,
            "completed_subtasks": task.completed_subtasks,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
        }


async def save_task_result(task_id: str, agent: str, subtask_index: int, result: str, success: bool = True):
    async with AsyncSessionLocal() as session:
        tr = TaskResult(
            task_id=task_id,
            agent=agent,
            subtask_index=subtask_index,
            result=result,
            success=success,
        )
        session.add(tr)
        await session.commit()


async def get_task_results(task_id: str) -> List[dict]:
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(TaskResult).where(TaskResult.task_id == task_id).order_by(TaskResult.subtask_index)
        )
        rows = res.scalars().all()
        return [{"agent": r.agent, "result": r.result, "success": r.success, "index": r.subtask_index} for r in rows]


async def save_failed_task(task_id: str, agent: str, instruction: str, error: str, retries: int):
    async with AsyncSessionLocal() as session:
        ft = FailedTask(task_id=task_id, agent=agent, instruction=instruction, error=error, retries=retries)
        session.add(ft)
        await session.commit()


async def write_log(task_id: str, component: str, message: str, level: str = "INFO"):
    async with AsyncSessionLocal() as session:
        log = Log(task_id=task_id, component=component, message=message, level=level)
        session.add(log)
        await session.commit()
