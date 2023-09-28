"""Test configuration."""

from pathlib import Path

import pytest

import boilercore
from boilercore import filter_certain_warnings
from boilercore.testing import get_session_path


# Can't be session scope
@pytest.fixture(autouse=True)
def _filter_certain_warnings():
    """Filter certain warnings."""
    filter_certain_warnings(package=boilercore.__name__)


@pytest.fixture(autouse=True, scope="session")
def project_session_path(tmp_path_factory) -> Path:
    """Project session path."""
    return get_session_path(tmp_path_factory, boilercore)


@pytest.fixture()
def params(project_session_path):
    """Parameters."""
    from boilercore.models.params import PARAMS

    return PARAMS
