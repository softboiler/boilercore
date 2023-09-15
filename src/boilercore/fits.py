"""Model fits."""

import warnings
from collections.abc import Mapping, Sequence
from functools import partial
from typing import Any
from warnings import catch_warnings

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from scipy.optimize import OptimizeWarning, curve_fit
from scipy.stats import t
from uncertainties import ufloat

from boilercore.types import Bound, Guess

MEASUREMENTS_COLOR = (0.2, 0.2, 0.2)


def fit_to_model(
    initial_values: Mapping[str, Guess],
    free_params: list[str],
    model: Any,
    confidence_interval: float,
    x: Any,
    y: Any,
    fixed_values: Any,
    model_bounds: Mapping[str, Bound] | None = None,
    fit_method: str = "trz",
    y_errors: Any = None,
):
    # Perform fit, filling "nan" on failure or when covariance computation fails
    with catch_warnings():
        warnings.simplefilter("error", category=OptimizeWarning)
        try:
            fitted_params, pcov = curve_fit(
                partial(model, **fixed_values),
                x,
                y,
                method=fit_method,
                p0=get_guesses(free_params, initial_values),
                bounds=(  # Expects ([L1, L2, L3], [H1, H2, H3])
                    tuple(zip(*get_bounds(free_params, model_bounds), strict=True))
                    if model_bounds
                    else (-np.inf, np.inf)
                ),
                sigma=None if y_errors is None else y_errors,
                absolute_sigma=y_errors is not None,
            )
        except (RuntimeError, OptimizeWarning):
            dim = len(free_params)
            fitted_params = np.full(dim, np.nan)
            pcov = np.full((dim, dim), np.nan)

    # Compute confidence interval
    standard_errors = np.sqrt(np.diagonal(pcov))
    errors = standard_errors * confidence_interval

    # Catching `OptimizeWarning` should be enough, but let's explicitly check for inf
    fitted_params = np.where(np.isinf(errors), np.nan, fitted_params)
    errors = np.where(np.isinf(errors), np.nan, errors)
    return fitted_params, errors


def get_guesses(
    params: Sequence[str], guesses: Mapping[str, Guess]
) -> tuple[Guess, ...]:
    """Compose guesses."""
    return tuple(guess for param, guess in guesses.items() if param in params)


def get_bounds(params: Sequence[str], bounds: Mapping[str, Bound]) -> tuple[Bound, ...]:
    """Compose bounds."""
    return tuple(bound for param, bound in bounds.items() if param in params)


def fit_and_plot(
    params: Any,
    model: Any,
    y: Any,
    run: str | None = None,
    y_errors: Any = None,
    ax: Axes | None = None,
) -> dict[str, float]:
    """Fit the model to the data and plot the results."""
    if not ax:
        _fig, ax = plt.subplots()
    x = params.geometry.rods["R"]
    fixed_values = params.fit.fixed_values
    model_fit, model_error = fit_to_model(
        model_bounds=params.fit.model_bounds,
        initial_values=params.fit.initial_values,
        free_params=params.fit.free_params,
        fit_method=params.fit.fit_method,
        model=model,
        confidence_interval=t.interval(0.95, 1)[1],
        x=x,
        y=y,
        fixed_values=fixed_values,
        y_errors=y_errors,
    )
    fit = dict(zip(params.fit.free_params, model_fit, strict=True))
    error = dict(zip(params.fit.free_errors, model_error, strict=True))
    plot_fit(
        ax=ax,
        run=run or "run",
        x=x,
        y=y,
        y_0=fit["T_s"],
        model=model,
        params=fit | fixed_values,
        **(  # type: ignore
            dict(
                y_errors=y_errors,
                errors=error | {k: 0 for k in params.fit.fixed_errors},
            )
            if y_errors is not None
            else {}
        ),
    )
    return {k: v for k, v in fit.items() if k in ["T_s", "q_s"]}


def plot_fit(
    run: str,
    model: Any,
    x: Sequence[Any],
    y: Sequence[Any],
    y_0: float,
    params: Mapping[str, Any],
    y_errors: Sequence[Any] | None = None,
    errors: Mapping[str, Any] | None = None,
    ax: plt.Axes | None = None,
):
    """Plot the model fit for a run."""

    # Setup
    if not ax:
        _fig, ax = plt.subplots()
    ax.margins(0, 0)
    ax.set_title(f"{run = }")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("T (C)")

    # Plot measurements
    ax.plot(x, y, ".", label="Measurements", color=MEASUREMENTS_COLOR, markersize=10)
    (xlim_min, xlim_max) = (0, max(x))
    pad = 0.025 * (xlim_max - xlim_min)
    x_smooth = np.linspace(xlim_min - pad, xlim_max + pad, 200)
    y_smooth = model(x_smooth, **params)
    ax.plot(x_smooth, y_smooth, "--", label="Model Fit")

    if y_errors is not None and errors is not None:
        _y_smooth, y_min, y_max = get_model_with_error(model, x_smooth, params, errors)
        ax.errorbar(x=x, y=y, yerr=y_errors, fmt="none", color=MEASUREMENTS_COLOR)  # type: ignore
        ax.fill_between(
            x=x_smooth,
            y1=y_min,  # type: ignore
            y2=y_max,  # type: ignore
            color=[0.8, 0.8, 0.8],
            edgecolor=[1, 1, 1],
            label="95% CI",
        )

    # Extrapolate
    ax.plot(0, y_0, "x", label="Extrapolation", color=[1, 0, 0])

    # Finish
    ax.legend()


def get_model_with_error(model, x, params, errors):
    """Evaluate the model for x and return y with errors."""
    u_x = [ufloat(v, 0, "x") for v in x]
    u_y = model(u_x, **combine_params_and_errors(params, errors))
    y = np.array([v.nominal_value for v in u_y])
    y_min = y - [v.std_dev for v in u_y]
    y_max = y + [v.std_dev for v in u_y]
    return y, y_min, y_max


def combine_params_and_errors(
    params: Mapping[str, Any], errors: Mapping[str, Any]
) -> dict[str, Any]:
    """Return parameters with errors given mappings, one with `_err`-suffixed keys."""
    return dict(
        zip(
            params.keys(),
            [
                ufloat(param, error, tag)
                for param, error, tag in zip(
                    params.values(),
                    {param: errors[f"{param}_err"] for param in params}.values(),
                    params.keys(),
                    strict=True,
                )
            ],
            strict=True,
        )
    )
