"""Test configuration."""

from collections.abc import Callable, Iterator
from functools import partial
from inspect import getclosurevars
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import seaborn as sns
from boilercore_dev.tests import EMPTY_NB
from boilercore_dev.tests.modelfun import FIT
from cachier import cachier, set_default_params  # pyright: ignore[reportMissingImports]

import boilercore
from boilercore.hashes import hash_args
from boilercore.models.params import Params
from boilercore.models.paths import Paths
from boilercore.notebooks import namespaces
from boilercore.notebooks.namespaces import (
    NO_PARAMS,
    get_cached_nb_ns,
    get_nb_ns,
    get_ns_attrs,
)
from boilercore.testing import get_session_path, unwrap_node
from boilercore.warnings import filter_boiler_warnings

MODELFUN = Path("src/boilercore/stages/modelfun.ipynb").resolve()


# Can't be session scope
@pytest.fixture(autouse=True)
def _filter_certain_warnings():
    """Filter certain warnings."""
    filter_boiler_warnings()


@pytest.fixture
def project_session_path(tmp_path_factory) -> Path:
    """Project session path."""
    return get_session_path(tmp_path_factory, boilercore)


@pytest.fixture
def params(project_session_path):
    """Parameters."""
    return Params(
        source=project_session_path / "params.yaml",
        paths=Paths(
            root=(root := project_session_path / "data"), models=root / "models"
        ),
    )


@pytest.fixture(scope="session")
def cache_dir(project_session_path) -> Path:
    """Cachier cache directory for tests."""
    cache_directory = project_session_path / ".cachier"
    set_default_params(cache_dir=cache_directory)
    return cache_directory


@pytest.fixture
def cached_function_and_cache_file(
    request, project_session_path
) -> Iterator[tuple[Callable[..., Any], Path]]:
    """Get cached minimal namespace suitable for passing to a receiving function."""
    cache_dir = project_session_path / ".cachier"
    cache_filename: Path | None = None

    def custom_cachier(fun: Callable[..., Any]):
        nonlocal cache_filename
        wrapper = cachier(hash_func=partial(hash_args, fun), cache_dir=cache_dir)(fun)
        cache_filename = Path(getclosurevars(wrapper).nonlocals["core"].cache_fname)

        return wrapper

    @custom_cachier
    def fun(
        nb: str = EMPTY_NB, params: namespaces.Params = NO_PARAMS
    ) -> SimpleNamespace:
        """Get cached minimal namespace suitable for passing to a receiving function."""
        return get_cached_nb_ns(nb, params, get_ns_attrs(unwrap_node(request.node)))

    if not cache_filename:
        raise RuntimeError("Cache file not set.")

    yield fun, cache_dir / cache_filename
    (cache_dir / cache_filename).unlink(missing_ok=True)


@pytest.fixture
def cached_function(cached_function_and_cache_file):  # noqa: D103
    return cached_function_and_cache_file[0]


@pytest.fixture
def cache_file(cached_function_and_cache_file):  # noqa: D103
    return cached_function_and_cache_file[1]


@pytest.fixture
def ns() -> SimpleNamespace:
    """Namespace for the model function notebook."""
    return get_nb_ns(MODELFUN.read_text(encoding="utf-8"))


@pytest.fixture
def model(params):
    """Deserialized model."""
    return FIT.get_models(params.paths.models)[1]


@pytest.fixture
def plt(plt):
    """Plot."""
    sns.set_theme(
        context="notebook", style="whitegrid", palette="bright", font="sans-serif"
    )
    yield plt
    plt.saveas = f"{plt.saveas[:-4]}.png"
