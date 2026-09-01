import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.study_planner import StudyTask, build_study_plan


def test_build_study_plan_preserves_order_and_capacity() -> None:
    tasks = [
        StudyTask(1, "فصل اول", 30),
        StudyTask(2, "فصل دوم", 25),
        StudyTask(3, "تمرین", 20),
    ]
    plan = build_study_plan(tasks, daily_minutes=55)
    assert [task.lesson_id for task in plan[0].tasks] == [1, 2]
    assert plan[0].total_minutes == 55
    assert [task.lesson_id for task in plan[1].tasks] == [3]


def test_build_study_plan_rejects_invalid_limits_and_tasks() -> None:
    with pytest.raises(ValueError):
        build_study_plan([], daily_minutes=0)
    with pytest.raises(ValueError):
        build_study_plan([StudyTask(1, "درس", 0)], daily_minutes=30)
    with pytest.raises(ValueError):
        build_study_plan([StudyTask(1, "درس", 60)], daily_minutes=30, max_days=1)


def test_study_plan_routes_require_authentication() -> None:
    client = TestClient(app)
    assert client.get("/api/v1/study-plan").status_code == 401
    assert client.patch("/api/v1/study-plan/tasks/1", json={"completed": True}).status_code == 401
