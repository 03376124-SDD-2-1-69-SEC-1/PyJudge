"""AI assignment generation package."""

from greader.ai.demo import DemoAssignmentGenerator
from greader.ai.interface import AssignmentGenerator, GenerationRequest
from greader.ai.schemas import (
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
