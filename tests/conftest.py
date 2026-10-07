from pathlib import Path

import pytest

from retailpulse.data.source import read_sources

pytest_plugins = ["tests.conftest_model"]


@pytest.fixture
def fixture_dir():
    return Path(__file__).parent / "fixtures/m5_synthetic"


@pytest.fixture
def sources(fixture_dir):
    return read_sources(fixture_dir)
