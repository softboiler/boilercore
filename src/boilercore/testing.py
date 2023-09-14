"""Test helpers."""

from pathlib import Path
from shutil import copy, copytree
from types import ModuleType, SimpleNamespace
from typing import Any, NamedTuple

import numpy as np
import pytest
from numpy.typing import ArrayLike
from ploomber_engine.ipython import PloomberClient
from scipy.stats import t

from boilercore.fits import fit_to_model
from boilercore.plotting import plot_fit


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


class MFParam(NamedTuple):
    run: str
    y: ArrayLike
    expected: dict[str, float]


def fit_and_plot(
    params: Any,
    model: Any,
    plt: ModuleType,
    run: str,
    y: Any,
) -> dict[str, float]:
    """Fit the model to the data and plot the results."""
    x = params.geometry.rods["R"]
    y_errors = [np.finfo(float).eps] * len(x)
    fixed_values = params.fit.fixed_values
    fixed_errors = {k: 0 for k in params.fit.fixed_errors}
    model_fit, model_error = fit_to_model(
        model_bounds=params.fit.model_bounds,
        initial_values=params.fit.initial_values,
        free_params=params.fit.free_params,
        fit_method=params.fit.fit_method,
        model=model,
        confidence_interval=t.interval(0.95, 1)[1],
        x=x,
        y=y,
        y_errors=y_errors,
        fixed_values=fixed_values,
    )
    fit = dict(zip(params.fit.free_params, model_fit, strict=True))
    error = dict(zip(params.fit.free_errors, model_error, strict=True))
    _fig, ax = plt.subplots()
    plot_fit(
        ax=ax,
        run=run,
        x=x,
        y=y,
        y_errors=y_errors,
        y_0=fit["T_s"],
        model=model,
        params=fit | fixed_values,
        errors=error | fixed_errors,
    )
    return {k: v for k, v in fit.items() if k in ["T_s", "q_s"]}
