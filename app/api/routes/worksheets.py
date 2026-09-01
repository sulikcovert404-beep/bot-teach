from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.security.dependencies import require_user
from app.services.worksheet import WorksheetQuestion, render_worksheet

router = APIRouter(prefix="/worksheets", tags=["worksheets"])


class WorksheetQuestionRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2_000)
    points: int = Field(default=1, ge=1, le=100)


class WorksheetRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    instructions: str = Field(min_length=1, max_length=4_000)
    questions: list[WorksheetQuestionRequest] = Field(min_length=1, max_length=100)


class WorksheetResponse(BaseModel):
    content: str
    format: str = "markdown"


@router.post("", response_model=WorksheetResponse)
async def create_worksheet(
    request: WorksheetRequest, _subject: str = Depends(require_user)
) -> WorksheetResponse:
    content = render_worksheet(
        request.title,
        request.instructions,
        [WorksheetQuestion(question.prompt, question.points) for question in request.questions],
    )
    return WorksheetResponse(content=content)
