"""Test helpers."""

from collections.abc import Callable, Iterator
from inspect import getmembers, isclass, isfunction
from pathlib import Path
from shutil import copytree
from types import ModuleType, SimpleNamespace
from typing import Any, NamedTuple, TypeAlias

import pytest
from numpy.typing import ArrayLike
from ploomber_engine._util import parametrize_notebook
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


NO_PARAMETERS = {}


def get_nb_namespace(
    nb_client: PloomberClient, parameters: dict[str, Any] = NO_PARAMETERS
) -> SimpleNamespace:
    """Copy a notebook and get its namespace."""
    if parameters:
        parametrize_notebook(nb_client._nb, parameters=parameters)  # noqa: SLF001
    return SimpleNamespace(**nb_client.get_namespace())


def get_nb_client(nb: Path) -> PloomberClient:
    """Copy a notebook and get its client."""
    return PloomberClient.from_path(nb)


class MFParam(NamedTuple):
    run: str
    y: ArrayLike
    expected: dict[str, float]


NotebookCase: TypeAlias = tuple[Path, dict[str, Any], Callable[[SimpleNamespace], Any]]


def get_notebook_cases(notebook: Path, cases: ModuleType) -> Iterator[NotebookCase]:
    """Get cases."""
    yield from (  # type: ignore
        pytest.param((notebook, parameters, fun), marks=marks, id=id)
        for fun, parameters, marks, id in walk_module_cases(cases)  # noqa: A001
    )


class Case(NamedTuple):
    fun: Callable[[SimpleNamespace], Any]
    parameters: dict[str, Any]
    marks: list[pytest.Mark]
    id: str  # noqa: A003


CASE_PREFIX = "case"
CASE = f"{CASE_PREFIX}_"


def walk_module_cases(cases: ModuleType) -> Iterator[Case]:
    """Walk a case module."""
    for case in (c.removeprefix(CASE) for c in dir(cases) if c.startswith(CASE)):
        if isclass(cls := getattr(cases, f"{CASE}{case}")):
            yield from walk_class_cases(cls)
        else:
            yield Case(fun=cls, parameters={}, marks=[], id=case)
    for casemap in (
        attr
        for name, attr in getmembers(cases)
        if isinstance(attr, dict) and name == f"{CASE_PREFIX}s"
    ):
        for fun, all_parameters in casemap.items():
            name = fun.__name__
            for i, parameters in enumerate(all_parameters):
                yield Case(fun=fun, parameters=parameters, marks=[], id=f"{name}_{i}")


def walk_class_cases(cls: type) -> Iterator[Case]:
    """Walk a case class."""
    case = cls.__name__.removeprefix(CASE)
    first_case = getmembers(cls, isfunction)[0][0]
    parameters = cls.parameters  # type: ignore
    marks = getattr(cls, "marks", [])
    all_parameters = (
        parameters
        # Basic check for dict of parameters rather than bare parameters dict
        if all(isinstance(p, dict) for p in parameters.values())
        else {first_case: parameters}
    )
    all_marks = (
        marks
        # Basic check for dict of markers rather than markers list
        if isinstance(marks, dict)
        else {first_case: marks}
    )
    for subcase, fun in getmembers(cls, isfunction):
        parameters = all_parameters[subcase]
        marks = all_marks[subcase]
        subcase = subcase.strip("_")
        yield Case(
            fun, parameters, marks, id="_".join([case, subcase]) if subcase else case
        )
