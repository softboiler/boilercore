"""Test helpers."""

from pathlib import Path
from shutil import copy, copytree
from types import ModuleType, SimpleNamespace

import pytest
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


def get_nb_client(nb_source: Path, session_path: Path) -> PloomberClient:
    """Copy a notebook and get its client."""
    nb = session_path / nb_source.name
    copy(nb_source, nb)
    return PloomberClient.from_path(nb)
