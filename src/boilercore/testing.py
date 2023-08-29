"""Test helpers."""

from contextlib import contextmanager
from pathlib import Path
from shutil import copy, copytree

import pytest
from ploomber_engine.ipython import PloomberClient


def get_nb_client(request, tmp_path, monkeypatch):
    """Prepare a temporary working directory and return a notebook client."""
    with before_tmp_workdir(tmp_path, monkeypatch):
        nb = tmp_path / request.param.name
        copy(request.param, nb)
    return PloomberClient.from_path(tmp_path / request.param.name)


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
