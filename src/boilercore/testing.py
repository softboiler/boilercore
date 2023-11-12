"""Test helpers."""

from collections.abc import Callable, Iterator
from inspect import getmembers, isclass, isfunction
from pathlib import Path
from shutil import copytree
from types import ModuleType, SimpleNamespace
from typing import Any, Literal, NamedTuple, TypeAlias

import pytest
from cachier import cachier
from cachier.core import _default_hash_func
from nbformat import NO_CONVERT, reads
from numpy.typing import ArrayLike
from ploomber_engine._util import parametrize_notebook
from ploomber_engine.ipython import PloomberClient


class MFParam(NamedTuple):
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


Fun: TypeAlias = Callable[[SimpleNamespace], Any]
Parameters: TypeAlias = dict[str, Any]
Results: TypeAlias = list[str]
Marks: TypeAlias = list[pytest.Mark]
NotebookCase: TypeAlias = tuple[Path, dict[str, Any], Fun]

NO_PARAMS = {}
NO_RESULTS = []
NO_MARKS = []


class Case(NamedTuple):
    fun: Fun
    parameters: Parameters
    results: Results
    marks: Marks
    id: str  # noqa: A003


def get_nb_namespace(
    nb: str, parameters: Parameters = NO_PARAMS, results: Results = NO_RESULTS
) -> dict[str, Any]:
    """Get notebook namespace, optionally parametrizing it."""
    nb_client = PloomberClient(reads(nb, as_version=NO_CONVERT))
    # We can't just `nb_client.execute(parameters=...)` since`nb_client.get_namespace()`
    # would execute all over again
    if parameters:
        parametrize_notebook(nb_client._nb, parameters=parameters)  # noqa: SLF001
    namespace = nb_client.get_namespace()
    return {result: namespace[result] for result in results} if results else namespace


def hash_get_nb_namespace_args(args, _kwds) -> str:
    """Hash function for cachier that freezes mappings."""
    nb: str
    parameters: Parameters = NO_PARAMS
    results: Results = NO_RESULTS
    nb, parameters, results = args
    return _default_hash_func(
        (nb, frozenset(parameters.items()), frozenset(results)), {}
    )


@cachier(hash_func=hash_get_nb_namespace_args)
def get_cached_nb_namespace(
    nb: str, parameters: Parameters = NO_PARAMS, results: Results = NO_RESULTS
) -> SimpleNamespace:
    """Get parametrized namespace."""
    ns_map = get_nb_namespace(nb, parameters=parameters)
    return SimpleNamespace(**{result: ns_map[result] for result in results})


def walk_notebook_cases(
    notebook: Path,
    cases: ModuleType,
    parameters: Parameters = NO_PARAMS,
    results: Results = NO_RESULTS,
    marks: Marks = NO_MARKS,
) -> Iterator[NotebookCase]:
    """Get cases."""
    yield from (  # type: ignore
        pytest.param((notebook, fun, parameters, results), marks=marks, id=id)
        for fun, parameters, results, marks, id in walk_module_cases(  # noqa: A001
            cases, parameters, results, marks
        )
    )


def walk_module_cases(
    cases: ModuleType,
    parameters: Parameters = NO_PARAMS,
    results: Results = NO_RESULTS,
    marks: Marks = NO_MARKS,
) -> Iterator[Case]:
    """Walk a case module."""
    members = {tuple(name.split("_")): attr for name, attr in getmembers(cases)}
    # First, bind module-level parameters, results, and marks
    for name, attr in members.items():
        match name:
            case ["parameters"]:
                parameters = attr
            case ["results"]:
                results = attr
            case ["marks"]:
                marks = attr
            case _:
                pass
    # Then, walk the rest of the module
    for name, attr in members.items():
        match name:
            case ["cases"]:
                yield from walk_mapping_cases(attr, parameters, results, marks)
            case ["case", *case] if isclass(attr):
                yield from walk_class_cases(attr, parameters, results, marks)
            case ["case", *case] if not isclass(attr):
                yield Case(attr, parameters, results, marks, id="_".join(case))
            case _:
                pass


def walk_mapping_cases(
    casemap: dict[Fun, list[dict[Literal["parameters", "results", "marks"], Any]]],
    parameters: Parameters = NO_PARAMS,
    results: Results = NO_RESULTS,
    marks: Marks = NO_MARKS,
) -> Iterator[Case]:
    """Walk a mapping."""
    yield from (
        Case(
            fun,
            cases.get("parameters", parameters),
            cases.get("results", results),
            cases.get("marks", marks),
            id=f"{fun.__name__}_{i}",
        )
        for fun, all_cases in casemap.items()
        for i, cases in enumerate(all_cases)
    )


def walk_class_cases(
    cls: type,
    parameters: Parameters = NO_PARAMS,
    results: Results = NO_RESULTS,
    marks: Marks = NO_MARKS,
) -> Iterator[Case]:
    """Walk a case class."""
    case = cls.__name__.removeprefix("case_")
    for subcase, fun in getmembers(cls, isfunction):
        subcase = subcase.strip("_")
        yield Case(
            fun,
            getattr(cls, "parameters", parameters),
            getattr(cls, "results", results),
            getattr(cls, "marks", marks),
            id="_".join([case, subcase]) if subcase else case,
        )
