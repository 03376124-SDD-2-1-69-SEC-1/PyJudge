import pytest

from tests.unit.core.generation.world import World


@pytest.fixture()
def world() -> World:
    return World()
