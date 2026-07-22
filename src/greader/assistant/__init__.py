"""AI assignment generation package."""

from greader.assistant.demo import DemoAssignmentGenerator
from greader.assistant.interface import AssignmentGenerator, GenerationRequest
from greader.assistant.schemas import (
    FullAssignmentDraft,
    GenerationMode,
    GenerationResult,
    TestCaseDraftSet,
)

__all__ = [
    "AssignmentGenerator",
    "DemoAssignmentGenerator",
    "FullAssignmentDraft",
    "GenerationMode",
    "GenerationRequest",
    "GenerationResult",
    "TestCaseDraftSet",
]
