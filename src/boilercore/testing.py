"""Test helpers."""

from contextlib import contextmanager
from pathlib import Path
from shutil import copy, copytree
from types import ModuleType

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


def get_nb_client(request: pytest.FixtureRequest, session_path: Path):
    """Prepare a temporary working directory and return a notebook client."""
    nb_source = request.param
    nb = session_path / nb_source.name
    copy(nb_source, nb)
    return PloomberClient.from_path(nb)


def tmp_workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Prepare a temporary working directory."""
    with before_tmp_workdir(tmp_path, monkeypatch):
        ...


@contextmanager
def before_tmp_workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Copy files over, allow changes, then change the working directory."""
    try:
        copytree(Path("tests") / "tmp_path", tmp_path, dirs_exist_ok=True)
        yield
    finally:
        monkeypatch.chdir(tmp_path)
