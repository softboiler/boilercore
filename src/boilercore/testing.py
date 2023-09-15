"""Test helpers."""

from pathlib import Path
from shutil import copytree
from types import ModuleType, SimpleNamespace
from typing import NamedTuple

import pytest
from numpy.typing import ArrayLike
from ploomber_engine.ipython import PloomberClient


def get_session_path(
    tmp_path_factory: pytest.TempPathFactory, package: ModuleType
) -> Path:
    """Copy test data to a session path and return the path."""
    test_data_name = Path("root")
    project_test_data = Path("tests") / test_data_name
    session_path = tmp_path_factory.getbasetemp() / test_data_name
    package.PROJECT_PATH = session_path  # type: ignore
    copytree(project_test_data, session_path, dirs_exist_ok=True)
    return session_path


def get_nb_namespace(nb_client: PloomberClient) -> SimpleNamespace:
    """Copy a notebook and get its namespace."""
    return SimpleNamespace(**nb_client.get_namespace())


def get_nb_client(nb: Path) -> PloomberClient:
    """Copy a notebook and get its client."""
    return PloomberClient.from_path(nb)


class MFParam(NamedTuple):
    run: str
    y: ArrayLike
    expected: dict[str, float]
