"""Client port for the generation use case.

`ai/client.py` satisfies this Protocol with a stub today and an HTTP adapter
later (OPS-04). Nothing in `core/` may import that adapter directly; only
`main.py` wires it in.
"""

from typing import Protocol

from greader.core.generation.schemas import GenerationRequest, GenerationResponse


class GenerationClient(Protocol):
    """Boundary to whatever produces an Assignment draft from a prompt."""

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Return a draft and its supporting citations."""
        ...
