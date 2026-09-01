from dataclasses import dataclass


@dataclass(frozen=True)
class StudyTask:
    lesson_id: int
    title: str
    minutes: int


@dataclass(frozen=True)
class PlannedDay:
    day_number: int
    tasks: tuple[StudyTask, ...]
    total_minutes: int


def build_study_plan(
    tasks: list[StudyTask], *, daily_minutes: int, max_days: int = 30
) -> list[PlannedDay]:
    if daily_minutes < 1 or max_days < 1:
        raise ValueError("Planning limits must be positive")
    if any(task.minutes < 1 for task in tasks):
        raise ValueError("Task duration must be positive")
    if any(task.minutes > daily_minutes for task in tasks):
        raise ValueError("Task duration exceeds daily capacity")
    plan: list[PlannedDay] = []
    remaining = list(tasks)
    while remaining and len(plan) < max_days:
        todays_tasks: list[StudyTask] = []
        total = 0
        while remaining and total + remaining[0].minutes <= daily_minutes:
            task = remaining.pop(0)
            todays_tasks.append(task)
            total += task.minutes
        if not todays_tasks:
            task = remaining.pop(0)
            todays_tasks.append(task)
            total = task.minutes
        plan.append(PlannedDay(len(plan) + 1, tuple(todays_tasks), total))
    if remaining:
        raise ValueError("Tasks do not fit within max_days")
    return plan
