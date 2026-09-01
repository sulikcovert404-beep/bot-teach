from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_session
from app.db.models import StudyPlan, StudyPlanTask
from app.security.dependencies import require_user
from app.services.study_planner import StudyTask, build_study_plan

router = APIRouter(prefix="/study-plan", tags=["study-plan"])


class StudyTaskRequest(BaseModel):
    lesson_id: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=255)
    minutes: int = Field(ge=1, le=240)


class StudyPlanRequest(BaseModel):
    tasks: list[StudyTaskRequest] = Field(max_length=500)
    daily_minutes: int = Field(ge=1, le=1_440)
    max_days: int = Field(default=30, ge=1, le=365)


class PlannedTaskResponse(BaseModel):
    lesson_id: int
    title: str
    minutes: int
    completed: bool = False


class StudyPlanTaskUpdate(BaseModel):
    completed: bool


class StudyPlanTaskResponse(BaseModel):
    id: int
    lesson_id: int
    day_number: int
    title: str
    minutes: int
    completed: bool


class PlannedDayResponse(BaseModel):
    day_number: int
    tasks: list[PlannedTaskResponse]
    total_minutes: int


@router.post("", response_model=list[PlannedDayResponse])
async def create_study_plan(
    request: StudyPlanRequest,
    subject: str = Depends(require_user),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> list[PlannedDayResponse]:
    try:
        user_id = int(subject)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid user identity") from exc
    plan = build_study_plan(
        [StudyTask(task.lesson_id, task.title, task.minutes) for task in request.tasks],
        daily_minutes=request.daily_minutes,
        max_days=request.max_days,
    )
    stored_plan = StudyPlan(user_id=user_id, daily_minutes=request.daily_minutes, max_days=request.max_days)
    stored_plan.tasks = [
        StudyPlanTask(
            lesson_id=task.lesson_id, day_number=day.day_number, title=task.title, minutes=task.minutes
        )
        for day in plan
        for task in day.tasks
    ]
    session.add(stored_plan)
    await session.commit()
    return [
        PlannedDayResponse(
            day_number=day.day_number,
            tasks=[PlannedTaskResponse(**task.__dict__) for task in day.tasks],
            total_minutes=day.total_minutes,
        )
        for day in plan
    ]


@router.patch("/tasks/{task_id}", response_model=StudyPlanTaskResponse)
async def update_study_task(
    task_id: int,
    request: StudyPlanTaskUpdate,
    subject: str = Depends(require_user),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> StudyPlanTask:
    try:
        user_id = int(subject)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid user identity") from exc
    task = await session.scalar(
        select(StudyPlanTask)
        .join(StudyPlan, StudyPlan.id == StudyPlanTask.plan_id)
        .where(StudyPlanTask.id == task_id, StudyPlan.user_id == user_id)
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Study plan task not found")
    task.completed = request.completed
    await session.commit()
    await session.refresh(task)
    return task


@router.get("", response_model=list[PlannedDayResponse])
async def list_latest_study_plan(
    subject: str = Depends(require_user),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> list[PlannedDayResponse]:
    try:
        user_id = int(subject)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid user identity") from exc
    plan = await session.scalar(
        select(StudyPlan).where(StudyPlan.user_id == user_id).order_by(StudyPlan.id.desc())
    )
    if plan is None:
        return []
    tasks = await session.scalars(select(StudyPlanTask).where(StudyPlanTask.plan_id == plan.id).order_by(StudyPlanTask.id))
    grouped: dict[int, list[PlannedTaskResponse]] = {}
    for task in tasks:
        grouped.setdefault(task.day_number, []).append(
            PlannedTaskResponse(
                lesson_id=task.lesson_id,
                title=task.title,
                minutes=task.minutes,
                completed=task.completed,
            )
        )
    return [
        PlannedDayResponse(day_number=day, tasks=items, total_minutes=sum(item.minutes for item in items))
        for day, items in grouped.items()
    ]
