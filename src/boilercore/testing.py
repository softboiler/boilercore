"""Helper functions for testing boiler code."""

from collections.abc import Iterable
from contextlib import contextmanager
from pathlib import Path
from re import compile
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


def walk_modules(package: Path, top: Path, suffix: str = ".py") -> Iterable[str]:
    """Walk modules from a given submodule path and the top level library directory."""
    for module in walk_module_paths(package, top, suffix):
        yield get_module(module, top)


def walk_module_paths(package: Path, top: Path, suffix: str = ".py") -> Iterable[Path]:
    """Walk modules from a given submodule path and the top level library directory."""
    for directory in (
        package,
        *[
            path
            for path in package.iterdir()
            if path.is_dir() and "__" not in str(path.relative_to(top.parent))
        ],
    ):
        yield from sorted(directory.glob(f"[!__]*{suffix}"))


def get_module(submodule: Path, library: Path) -> str:
    """Get module name given the submodule path and the top level library directory."""
    return (
        str(submodule.relative_to(library.parent).with_suffix(""))
        .replace("\\", ".")
        .replace("/", ".")
    )


def get_module_rel(module: str, relative: str) -> str:
    """Get module name relative to another module."""
    return compile(rf".*{relative}\.").sub(repl="", string=module)
