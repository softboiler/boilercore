"""Model fits."""

import warnings
from collections.abc import Mapping, Sequence
from functools import partial
from typing import Any, Literal
from warnings import catch_warnings

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from scipy.optimize import OptimizeWarning, curve_fit
from scipy.stats import t
from uncertainties import ufloat

from boilercore.models.fit import Fit
from boilercore.types import Bound, Guess

XY_COLOR = (0.2, 0.2, 0.2)
"""Default color for measurement points."""

CONFIDENCE_INTERVAL_95 = t.interval(0.95, 1)[1]
"""Confidence interval for a single sample from a student's t-distribution."""


def fit_and_plot(
    model: Any,
    params: Fit,
    x: Any,
    y: Any,
    y_errors: Any = None,
    confidence_interval=CONFIDENCE_INTERVAL_95,
    ax: Axes | None = None,
    run: str | None = None,
) -> tuple[dict[str, float], dict[str, float]]:
    """Get fits and errors for project model and plot the results."""
    if not ax:
        _fig, ax = plt.subplots()
    fits, errors = fit_from_params(
        model=model,
        params=params,
        x=x,
        y=y,
        y_errors=y_errors,
        confidence_interval=confidence_interval,
    )
    plot_fit(
        model=model,
        x=x,
        y=y,
        y_0=fits["T_s"],
        params=fits | params.fixed_values,
        errors=errors | dict.fromkeys(params.fixed_errors, 0),
        y_errors=y_errors if y_errors is not None else None,
        ax=ax,
        run=run or "run",
    )
    return fits, errors


def fit_from_params(
    model: Any,
    params: Fit,
    x: Any,
    y: Any,
    y_errors: Any = None,
    confidence_interval: float = CONFIDENCE_INTERVAL_95,
) -> tuple[dict[str, float], dict[str, float]]:
    """Get fits and errors for project model."""
    fits, errors = fit(
        model=model,
        fixed_values=params.fixed_values,
        free_params=params.free_params,
        initial_values=params.initial_values,
        model_bounds=params.model_bounds,
        x=x,
        y=y,
        y_errors=y_errors,
        confidence_interval=confidence_interval,
    )
    return (
        dict(zip(params.free_params, fits, strict=True)),
        dict(zip(params.free_errors, errors, strict=True)),
    )


def fit(
    model: Any,
    fixed_values: Any,
    free_params: list[str],
    initial_values: Mapping[str, Guess],
    model_bounds: Mapping[str, Bound],
    x: Any,
    y: Any,
    y_errors: Any = None,
    confidence_interval: float = CONFIDENCE_INTERVAL_95,
    method: Literal["trf", "dogbox"] = "trf",
) -> tuple[Any, Any]:
    """Get fits and errors."""
    # Perform fit, filling "nan" on failure or when covariance computation fails
    with catch_warnings():
        warnings.simplefilter("error", category=OptimizeWarning)
        try:
            fits, pcov = curve_fit(
                f=partial(model, **fixed_values),
                p0=get_guesses(free_params, initial_values),
                # Expects e.g. ([L1, L2, L3], [H1, H2, H3])
                bounds=tuple(zip(*get_bounds(free_params, model_bounds), strict=True)),
                xdata=x,
                ydata=y,
                sigma=None if y_errors is None else y_errors,
                absolute_sigma=y_errors is not None,
                method=method,
            )
        except (RuntimeError, OptimizeWarning):
            dim = len(free_params)
            fits = np.full(dim, np.nan)
            pcov = np.full((dim, dim), np.nan)

    # Compute confidence interval
    standard_errors = np.sqrt(np.diagonal(pcov))
    errors = standard_errors * confidence_interval

    # Catching `OptimizeWarning` should be enough, but let's explicitly check for inf
    fits = np.where(np.isinf(errors), np.nan, fits)
    errors = np.where(np.isinf(errors), np.nan, errors)
    return fits, errors


def get_guesses(
    params: Sequence[str], guesses: Mapping[str, Guess]
) -> tuple[Guess, ...]:
    """Compose guesses."""
    return tuple(guess for param, guess in guesses.items() if param in params)


def get_bounds(params: Sequence[str], bounds: Mapping[str, Bound]) -> tuple[Bound, ...]:
    """Compose bounds."""
    return tuple(bound for param, bound in bounds.items() if param in params)


def plot_fit(
    model: Any,
    x: Any,
    y: Any,
    y_0: float,
    params: Mapping[str, Any],
    errors: Mapping[str, Any],
    y_errors: Sequence[Any] | None = None,
    ax: Axes | None = None,  # type: ignore
    run: str | None = None,
):
    """Plot a model fit."""
    if not ax:
        _fig, ax = plt.subplots()
        ax: Axes
    ax.margins(0, 0)
    ax.set_title(f"{run = }" if run else "run")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("T (C)")

    # Plot measurements
    ax.plot(x, y, ".", label="Measurements", color=XY_COLOR, markersize=10)
    (xlim_min, xlim_max) = (0, max(x))
    pad = 0.025 * (xlim_max - xlim_min)
    x_smooth = np.linspace(xlim_min - pad, xlim_max + pad, 200)
    y_smooth, y_min, y_max = get_model_with_error(model, x_smooth, params, errors)
    ax.plot(x_smooth, y_smooth, "--", label="Model Fit")

    # Plot measurement errors
    if y_errors is not None:
        ax.errorbar(x=x, y=y, yerr=y_errors, fmt="none", color=XY_COLOR)

    # Plot confidence band
    ax.fill_between(
        x=x_smooth,
        y1=y_min,  # type: ignore  # pyright 1.1.333
        y2=y_max,  # type: ignore  # pyright 1.1.333
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
