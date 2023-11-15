"""Test helpers."""

import ast
from ast import NodeVisitor
from collections import defaultdict
from collections.abc import Callable, Iterator
from inspect import getmembers, getsource, isclass, isfunction
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


Params: TypeAlias = dict[str, Any]
Results: TypeAlias = list[str]

NO_PARAMS = {}
ALL_RESULTS_DEFAULT = False
NO_RESULTS = []


def get_nb_namespace(
    nb: str,
    params: Params = NO_PARAMS,
    all_results: bool = False,
    results: Results = NO_RESULTS,
) -> SimpleNamespace:
    """Get notebook namespace, optionally parametrizing it."""
    nb_client = get_nb_client(nb)
    # We can't just `nb_client.execute(params=...)` since`nb_client.get_namespace()`
    # would execute all over again
    if params:
        parametrize_notebook(nb_client._nb, parameters=params)  # noqa: SLF001
    namespace = nb_client.get_namespace()
    return SimpleNamespace(
        **(
            namespace
            if all_results
            else {result: namespace[result] for result in results}
        )
    )


def hash_get_nb_namespace_args(args, kwds) -> str:
    """Freeze arguments to make them hashable."""
    keys = ["nb", "params", "all_results", "results"]
    nb, params, all_results, results = (
        dict(zip(keys, [None, NO_PARAMS, ALL_RESULTS_DEFAULT, NO_RESULTS], strict=True))
        | kwds
        | dict(zip(keys, args, strict=False))
    ).values()
    return _default_hash_func(
        args=(nb, frozenset(params.items()), all_results, frozenset(results)), kwds={}
    )


@cachier(hash_func=hash_get_nb_namespace_args)
def get_cached_nb_namespace(
    nb: str,
    params: Params = NO_PARAMS,
    all_results: bool = ALL_RESULTS_DEFAULT,
    results: Results = NO_RESULTS,
) -> SimpleNamespace:
    """Get notebook namespace with caching."""
    return get_nb_namespace(nb, params, all_results, results)


def get_nb_client(nb: str):
    """Get notebook client."""
    return PloomberClient(reads(nb, as_version=NO_CONVERT))


def get_accessed_attributes(source: str, namespace: str) -> list[str]:
    """Get attributes accessed in a particular namespace in source code."""
    accessed_attributes = AccessedAttributesVisitor()
    accessed_attributes.visit(ast.parse(source))
    return list(accessed_attributes.names[namespace])


class AccessedAttributesVisitor(NodeVisitor):
    def __init__(self):
        """Maps accessed attributes to their namespaces."""
        self.names: dict[str, set[str]] = defaultdict(set)

    def visit_Attribute(self, node: ast.Attribute):  # noqa: N802
        if isinstance(node.value, ast.Name):
            self.names[node.value.id].add(node.attr)
        self.generic_visit(node)


def get_source(node) -> str:
    """Get the source code of a pytest node."""
    return getsource(getattr(node.module, node.originalname))


Fun: TypeAlias = Callable[[SimpleNamespace], Any]
NotebookCase: TypeAlias = tuple[Path, dict[str, Any], Fun]
Marks: TypeAlias = list[pytest.Mark]

NO_MARKS = []


def walk_notebook_cases(
    notebook: Path,
    cases: ModuleType,
    params: Params = NO_PARAMS,
    results: Results = NO_RESULTS,
    marks: Marks = NO_MARKS,
) -> Iterator[NotebookCase]:
    """Get cases."""
    yield from (  # type: ignore
        pytest.param((notebook, fun, params, results), marks=marks, id=id)
        for fun, params, results, marks, id in walk_module_cases(  # noqa: A001
            cases, params, results, marks
        )
    )


class Case(NamedTuple):
    fun: Fun
    params: Params
    results: Results
    marks: Marks
    id: str  # noqa: A003


def walk_module_cases(
    cases: ModuleType,
    params: Params = NO_PARAMS,
    results: Results = NO_RESULTS,
    marks: Marks = NO_MARKS,
) -> Iterator[Case]:
    """Walk a case module."""
    members = {tuple(name.split("_")): attr for name, attr in getmembers(cases)}
    # First, bind module-level params, results, and marks
    for name, attr in members.items():
        match name:
            case ["params"]:
                params = attr
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
                yield from walk_mapping_cases(attr, params, results, marks)
            case ["case", *_] if isclass(attr):
                yield from walk_class_cases(attr, params, results, marks)
            case ["case", *case] if not isclass(attr):
                yield Case(attr, params, results, marks, id="_".join(case))
            case _:
                pass


def walk_mapping_cases(
    casemap: dict[Fun, list[dict[Literal["params", "results", "marks"], Any]]],
    params: Params = NO_PARAMS,
    results: Results = NO_RESULTS,
    marks: Marks = NO_MARKS,
) -> Iterator[Case]:
    """Walk a mapping."""
    yield from (
        Case(
            fun,
            cases.get("params", params),
            cases.get("results", results),
            cases.get("marks", marks),
            id=f"{fun.__name__}_{i}",
        )
        for fun, all_cases in casemap.items()
        for i, cases in enumerate(all_cases)
    )


def walk_class_cases(
    cls: type,
    params: Params = NO_PARAMS,
    results: Results = NO_RESULTS,
    marks: Marks = NO_MARKS,
) -> Iterator[Case]:
    """Walk a case class."""
    case = cls.__name__.removeprefix("case_")
    for subcase, fun in getmembers(cls, isfunction):
        subcase = subcase.strip("_")
        yield Case(
            fun,
            getattr(cls, "params", params),
            getattr(cls, "results", results),
            getattr(cls, "marks", marks),
            id="_".join([case, subcase]) if subcase else case,
        )
