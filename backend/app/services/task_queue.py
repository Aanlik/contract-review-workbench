"""Simple background task queue using threads.

Stores task results in-memory and optionally in the database.
Designed for OCR and AI review jobs that should not block the HTTP request.
"""

from __future__ import annotations

import traceback
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


@dataclass
class TaskResult:
    task_id: str
    status: TaskStatus
    result: Any = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    finished_at: datetime | None = None
    progress: str = ""
    progress_percent: int = 0
    current_step: int = 0
    total_steps: int = 0


class TaskQueue:
    """In-process background task queue backed by a thread pool."""

    def __init__(self, max_workers: int = 2) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._tasks: dict[str, TaskResult] = {}
        self._counter = 0

    def submit(self, fn: Callable[..., Any], *args: Any, label: str = "") -> TaskResult:
        self._counter += 1
        task_id = f"task-{self._counter}"
        result = TaskResult(task_id=task_id, status=TaskStatus.queued)
        self._tasks[task_id] = result
        future = self._executor.submit(self._run, task_id, fn, args)
        future.add_done_callback(lambda _: None)
        return result

    def get(self, task_id: str) -> TaskResult | None:
        return self._tasks.get(task_id)

    def list_tasks(self) -> list[TaskResult]:
        return sorted(self._tasks.values(), key=lambda t: t.created_at, reverse=True)
    def reset(self) -> None:
        self._tasks.clear()
        self._counter = 0

    def update_progress(self, task_id: str, progress: str, step: int = 0, total: int = 0, percent: int = 0) -> None:
        """Update progress for a running task. Safe to call from worker threads."""
        task = self._tasks.get(task_id)
        if task is None:
            return
        task.progress = progress
        task.current_step = step
        task.total_steps = total
        task.progress_percent = percent if percent > 0 else (int(step / total * 100) if total > 0 else 0)

    def _run(self, task_id: str, fn: Callable[..., Any], args: tuple[Any, ...]) -> None:
        task = self._tasks[task_id]
        task.status = TaskStatus.running
        task.started_at = datetime.now(UTC)
        try:
            task.result = fn(task_id, *args)
            task.status = TaskStatus.completed
            task.progress_percent = 100
        except Exception as exc:
            task.status = TaskStatus.failed
            task.error = f"{exc}\n{traceback.format_exc()}"
        finally:
            task.finished_at = datetime.now(UTC)


task_queue = TaskQueue(max_workers=2)
