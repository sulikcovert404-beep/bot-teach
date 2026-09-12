import pytest

from app.services.content_commands import (
    ApproveContentVersionCommand,
    CreateContentVersionCommand,
    PublishRequestContract,
)
from app.services.curriculum_pipeline_api import ContentValidationError


def test_command_validation_preserves_persian_text_and_serializes_stably() -> None:
    command = CreateContentVersionCommand("key", "hash", 3, "درسِ می‌رود \u200c")
    assert "می‌رود" in command.serialize()
    assert command.serialize() == command.serialize()


def test_invalid_command_inputs_are_typed() -> None:
    with pytest.raises(ContentValidationError):
        PublishRequestContract("k", "h", 0, 1)
    with pytest.raises(ContentValidationError):
        ApproveContentVersionCommand("k", "h", 1, "", 1)
