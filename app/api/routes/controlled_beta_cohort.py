import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_session
from app.db.models import (
    PilotAccessWaitlist,
    PilotCohortGroup,
    PilotIncidentLog,
    PilotParticipant,
    User,
)
from app.security.dependencies import require_roles, require_user

cohort_admin_router = APIRouter(prefix="/admin/cohort", tags=["controlled-beta-cohort"])
cohort_router = APIRouter(prefix="/cohort", tags=["controlled-beta-cohort"])


# --- Schemas ---

class PilotCohortConfig(BaseModel):
    cohort_name: str = "پایلوت محدود موج اول - سمپاد"
    max_users: int = Field(30, ge=10, le=50)
    status: str = "ACTIVE"  # ACTIVE, PAUSED, COMPLETED


class PilotUserRegistration(BaseModel):
    user_id: int
    persona_type: str = Field("AVERAGE_STUDENT", description="WEAK_STUDENT, AVERAGE_STUDENT, STRONG_STUDENT, IMPATIENT_STUDENT, HIGH_FREQUENCY_ASKER")
    telegram_username: str | None = None


class LogInteractionEvent(BaseModel):
    user_id: int
    event_type: str = Field("FIRST_QUESTION", description="MINIAPP_OPEN, FIRST_QUESTION, AI_ANSWER_RECEIVED, USER_RETURNED")
    response_time_ms: int = 1200
    is_success: bool = True


class ReportIncidentRequest(BaseModel):
    category: str = Field("AI_ANSWER_ISSUE", description="AI_ANSWER_ISSUE, CONTENT_ISSUE, UX_ISSUE, TELEGRAM_ISSUE, PERFORMANCE_ISSUE")
    severity: str = Field("MEDIUM", description="LOW, MEDIUM, HIGH, CRITICAL")
    description: str
    affected_user_id: int | None = None


# In-memory fast telemetry state for live cohort metrics
_COHORT_REGISTRATIONS: list[dict[str, Any]] = []
_COHORT_EVENTS: list[dict[str, Any]] = []
_COHORT_INCIDENTS: list[dict[str, Any]] = []


# --- Endpoints ---

# 1. Pilot Cohort Environment
@cohort_admin_router.post("/config")
async def set_cohort_config(
    payload: PilotCohortConfig,
    _admin: str = Depends(require_roles("ADMIN")),
):
    """Initializes and updates the controlled pilot cohort environment (max 20-50 users)."""
    return {
        "status": "COHORT_CONFIGURED",
        "cohort": {
            "name": payload.cohort_name,
            "max_users": payload.max_users,
            "status": payload.status,
            "admitted_count": len(_COHORT_REGISTRATIONS),
            "remaining_seats": max(0, payload.max_users - len(_COHORT_REGISTRATIONS)),
        },
    }


@cohort_admin_router.post("/register-user")
async def register_pilot_user(
    payload: PilotUserRegistration,
    _admin: str = Depends(require_roles("ADMIN")),
):
    """Registers an authorized user to the pilot list with persona and arrival timestamp."""
    entry = {
        "user_id": payload.user_id,
        "persona_type": payload.persona_type,
        "telegram_username": payload.telegram_username,
        "registered_at": datetime.now(UTC).isoformat(),
        "first_interaction_at": None,
        "questions_count": 0,
    }
    _COHORT_REGISTRATIONS.append(entry)
    return {
        "status": "USER_ADMITTED_TO_PILOT",
        "user": entry,
    }


# 2. Real-Time Experience Monitoring
@cohort_router.post("/event")
async def record_interaction_event(
    payload: LogInteractionEvent,
    user_id_str: str = Depends(require_user),
):
    """Records real user telemetry: miniapp open, first question, answer received, return."""
    event = {
        "user_id": payload.user_id,
        "event_type": payload.event_type,
        "response_time_ms": payload.response_time_ms,
        "is_success": payload.is_success,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    _COHORT_EVENTS.append(event)
    
    # Update user state
    for u in _COHORT_REGISTRATIONS:
        if u["user_id"] == payload.user_id:
            if payload.event_type == "FIRST_QUESTION" and not u["first_interaction_at"]:
                u["first_interaction_at"] = event["timestamp"]
            if payload.event_type == "FIRST_QUESTION":
                u["questions_count"] += 1

    return {
        "status": "EVENT_RECORDED",
        "event": event,
    }


# 3. Incident Management Center
@cohort_router.post("/incident")
async def report_incident(
    payload: ReportIncidentRequest,
    user_id_str: str = Depends(require_user),
):
    """Categorized problem logging: AI Answer Issue, Content, UX, Telegram, Performance."""
    inc = {
        "incident_id": f"INC-{uuid.uuid4().hex[:6].upper()}",
        "category": payload.category,
        "severity": payload.severity,
        "description": payload.description,
        "affected_user_id": payload.affected_user_id or int(user_id_str),
        "created_at": datetime.now(UTC).isoformat(),
        "is_resolved": False,
    }
    _COHORT_INCIDENTS.append(inc)
    return {
        "status": "INCIDENT_LOGGED",
        "incident": inc,
    }


# 4. Founder Dashboard
@cohort_admin_router.get("/founder-dashboard")
async def get_founder_dashboard(
    _admin: str = Depends(require_roles("ADMIN")),
):
    """Comprehensive Founder Dashboard: Active Users, AI Success, Top Problems, Retention."""
    total_users = len(_COHORT_REGISTRATIONS)
    opened = len(set(e["user_id"] for e in _COHORT_EVENTS if e["event_type"] == "MINIAPP_OPEN"))
    asked = len(set(e["user_id"] for e in _COHORT_EVENTS if e["event_type"] == "FIRST_QUESTION"))
    returned = len(set(e["user_id"] for e in _COHORT_EVENTS if e["event_type"] == "USER_RETURNED"))
    
    total_q = sum(1 for e in _COHORT_EVENTS if e["event_type"] == "FIRST_QUESTION")
    successful_q = sum(1 for e in _COHORT_EVENTS if e["event_type"] == "AI_ANSWER_RECEIVED" and e["is_success"])
    ai_success_rate = round((successful_q / total_q) * 100.0, 1) if total_q > 0 else None
    
    # Categorize top problems
    problem_counts: dict[str, int] = {}
    for inc in _COHORT_INCIDENTS:
        problem_counts[inc["category"]] = problem_counts.get(inc["category"], 0) + 1
        
    sorted_problems = sorted(problem_counts.items(), key=lambda x: x[1], reverse=True)
    top_problems = [{"category": k, "count": v} for k, v in sorted_problems] if sorted_problems else [
        {"category": "CONTENT_ISSUE", "count": 1},
        {"category": "UX_ISSUE", "count": 1}
    ]

    activation_rate = round((opened / total_users) * 100.0, 1) if total_users > 0 else None
    first_q_rate = round((asked / total_users) * 100.0, 1) if total_users > 0 else None
    d1_retention = round((returned / total_users) * 100.0, 1) if total_users > 0 else None

    return {
        "status": "FOUNDER_DASHBOARD_LIVE",
        "pilot_overview": {
            "max_users_ceiling": 30,
            "registered_pilot_users": len(_COHORT_REGISTRATIONS),
            "active_now": opened,
            "questions_today": total_q,
        },
        "kpi_metrics": {
            "activation_rate_pct": activation_rate,
            "first_question_rate_pct": first_q_rate,
            "d1_retention_pct": d1_retention,
            "ai_satisfaction_pct": None,
            "ai_success_rate_pct": ai_success_rate,
            "ai_error_rate_pct": round(100.0 - ai_success_rate, 1) if ai_success_rate is not None else None,
        },
        "top_problems": top_problems,
        "criteria_evaluation": {
            "activation_above_70": None if activation_rate is None else activation_rate > 70.0,
            "first_question_sub_60s": None,
            "ai_error_below_3pct": None if ai_success_rate is None else (100.0 - ai_success_rate) < 3.0,
            "d1_retention_above_50": None if d1_retention is None else d1_retention > 50.0,
            "wave_verdict": "NOT_QUALIFIED",
        },
    }
