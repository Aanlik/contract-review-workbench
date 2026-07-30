from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.task_queue import task_queue

router = APIRouter()


class TaskRead(BaseModel):
    task_id: str
    status: str
    result: object | None = None
    error: str | None = None
    progress: str = ""
    progress_percent: int = 0
    current_step: int = 0
    total_steps: int = 0
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None


def _serialize(task) -> TaskRead:
    return TaskRead(
        task_id=task.task_id,
        status=task.status.value,
        result=task.result,
        error=task.error,
        progress=task.progress,
        progress_percent=task.progress_percent,
        current_step=task.current_step,
        total_steps=task.total_steps,
        created_at=task.created_at.isoformat(),
        started_at=task.started_at.isoformat() if task.started_at else None,
        finished_at=task.finished_at.isoformat() if task.finished_at else None,
    )


@router.get("", response_model=list[TaskRead])
def list_tasks():
    return [_serialize(t) for t in task_queue.list_tasks()]


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: str):
    task = task_queue.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return _serialize(task)
