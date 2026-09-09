from dataclasses import dataclass


@dataclass
class TestCase:
    id: int | None
    assignment_id: int
    input_data: str
    expected_output: str
    is_hidden: bool = False
    order_index: int = 0
