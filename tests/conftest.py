from pathlib import Path

import pytest

from retailpulse.data.source import read_sources


@pytest.fixture
def fixture_dir():
    return Path(__file__).parent / "fixtures/m5_synthetic"


@pytest.fixture
def sources(fixture_dir):
    return read_sources(fixture_dir)
