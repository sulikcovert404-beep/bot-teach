from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

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


class PlannedDayResponse(BaseModel):
    day_number: int
    tasks: list[PlannedTaskResponse]
    total_minutes: int


@router.post("", response_model=list[PlannedDayResponse])
async def create_study_plan(
    request: StudyPlanRequest, _subject: str = Depends(require_user)
) -> list[PlannedDayResponse]:
    plan = build_study_plan(
        [StudyTask(task.lesson_id, task.title, task.minutes) for task in request.tasks],
        daily_minutes=request.daily_minutes,
        max_days=request.max_days,
    )
    return [
        PlannedDayResponse(
            day_number=day.day_number,
            tasks=[PlannedTaskResponse(**task.__dict__) for task in day.tasks],
            total_minutes=day.total_minutes,
        )
        for day in plan
    ]
