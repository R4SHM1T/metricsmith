from pathlib import Path

import pytest

from metricsmith import Runtime, SemanticLayer, demo_connection

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture
def layer() -> SemanticLayer:
    return SemanticLayer.from_dir(str(EXAMPLES / "semantic"))


@pytest.fixture
def runtime(layer) -> Runtime:
    return Runtime(layer, demo_connection())
