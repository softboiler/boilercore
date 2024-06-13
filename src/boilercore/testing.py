"""Test helpers."""

from collections.abc import Callable
from pathlib import Path
from shutil import copytree
from types import ModuleType
from typing import Any, NamedTuple

import pytest
from _pytest.python import Function
from numpy.typing import ArrayLike


class MFParam(NamedTuple):
    """Parameter for model function tests."""

    run: str
    y: ArrayLike
    expected: dict[str, float]


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


def unwrap_node(node: Function) -> Callable[..., Any]:
    """Unwrap a pytest node."""
    return getattr(node.module, node.originalname)
