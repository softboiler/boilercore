"""Model fits."""

import warnings
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from functools import partial, wraps
from math import isnan
from pathlib import Path
from sys import version_info
from typing import Any, Literal
from warnings import catch_warnings, warn

import dill
import numpy
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from numpy import array, finfo, inf, vectorize
from scipy.optimize import OptimizeWarning, curve_fit
from scipy.stats import t
from sympy import Symbol, lambdify
from uncertainties import ufloat
from uncertainties.umath import exp, sqrt  # pyright: ignore[reportAttributeAccessIssue]

from boilercore.types import Bound, Guess

EPS: float = finfo(float).eps  # pyright: ignore[reportAssignmentType]
"""Minimum positive value to avoid divide-by-zero for affected parameters."""
MIN_CONVECTION_COEFF = 1e-3
"""Minimum positive convection coefficient to avoid instability of exponents."""
INIT_CONVECTION_COEFF = 1.0
"""An initial guess not too close to zero to avoid iteration instability."""
MIN_TEMP = 1e-3
"""Minimum temperature to avoid instability near absolute zero."""


def fix_model(f) -> Callable[..., Any]:
    """Fix edge-cases of lambdify where all inputs must be arrays.

    See the notes section in the link below where it says, "However, in some cases
    the generated function relies on the input being a numpy array."

    https://docs.sympy.org/latest/modules/utilities/lambdify.html#sympy.utilities.lambdify.lambdify
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        result = f(
            *(array(arg) for arg in args), **{k: array(v) for k, v in kwargs.items()}
        )

        return result if result.size > 1 else result.item()

    return wrapper


def get_model_errors(params: list[Symbol]) -> list[str]:
    """Get error parameters for model parameters."""
    return [f"{param.name}_err" for param in params]


@dataclass
class Fit:
    """Model fit."""

    fit_method: Literal["trf", "dogbox"] = "trf"
    """Model fit method."""
    independent_params: list[str] = field(default_factory=lambda: ["x"])
    """Independent parameters."""
    free_params: list[str] = field(default_factory=lambda: ["T_s", "q_s", "h_a"])
    """Free parameters."""
    fixed_params: list[str] = field(
        default_factory=lambda: ["h_w", "r", "T_infa", "T_infw", "x_s", "x_wa", "k"]
    )
    """Parameters to fix. Evaluated before fitting, overridable in code."""
    bounds: dict[str, tuple[float, float]] = field(
        default_factory=lambda: {
            "T_s": (MIN_TEMP, inf),
            "q_s": (-inf, inf),
            "h_w": (MIN_CONVECTION_COEFF, inf),
            "h_a": (MIN_CONVECTION_COEFF, inf),
            "r": (EPS, inf),
            "T_infa": (MIN_TEMP, inf),
            "T_infw": (MIN_TEMP, inf),
            "x_s": (-inf, inf),
            "x_wa": (-inf, inf),
            "k": (EPS, inf),
        }
    )
    """Bounds of model parameters."""
    values: dict[str, float] = field(
        default_factory=lambda: {
            "T_s": 105.0,  # (K)
            "q_s": 2e5,  # (W/m^2)
            "h_w": INIT_CONVECTION_COEFF,  # (W/m^2-K)
            "h_a": INIT_CONVECTION_COEFF,  # (W/m^2-K)
            "r": 0.0047625,  # (m)
            "T_infa": 25.0,  # (K)
            "T_infw": 100.0,  # (K)
            "x_s": 0.0,  # (m)
            "x_wa": 0.0381,  # (m) Distance from collar surface to chamber floor, plus protuberance
            "k": 400.0,  # (W/m-K)
        }
    )
    """Values of model parameters."""

    @property
    def errors(self) -> list[str]:
        """Error parameters for each free parameter."""
        return [f"{param}_err" for param in self.free_params]

    @property
    def fixed_values(self) -> dict[str, float]:
        """Fixed values for each fixed parameter."""
        return {p: v for p, v in self.values.items() if p in self.fixed_params}

    @property
    def fixed_errors(self) -> list[str]:
        """Error parameters for each fixed parameter."""
        return [f"{p}_err" for p in self.fixed_params]

    @property
    def free_errors(self) -> list[str]:
        """Error parameters for each free parameter."""
        return [f"{p}_err" for p in self.free_params]

    @property
    def params_and_errors(self) -> list[str]:
        """Model parameters and their errors."""
        return [
            *self.free_params,
            *self.fixed_params,
            *self.free_errors,
            *self.fixed_errors,
        ]

    def get_models(self, models: Path) -> tuple[Callable[..., Any], Callable[..., Any]]:
        """Unpickle the model function for fitting data."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", dill.UnpicklingWarning)
            expr = dill.loads(
                Path(
                    models
                    / f"modelfun-{'.'.join([str(elem) for elem in version_info[:2]])}.dillpickle"
                ).read_bytes()
            )
        params = {p.name: p for p in expr.free_symbols}
        args = [
            params[p]
            for p in [*self.independent_params, *self.free_params, *self.fixed_params]
        ]
        model = lambdify(args=args, expr=expr, modules=numpy)
        overrides = {f.name: vectorize(f) for f in (exp, sqrt)}
        model_with_uncertainty = lambdify(
            args=args, expr=expr, modules=[overrides, numpy]
        )
        return partial(model, **self.fixed_values), fix_model(
            partial(model_with_uncertainty, **self.fixed_values)
        )


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
        _fig, ax = plt.subplots()  # pyright: ignore[reportAssignmentType]
    fits, errors = fit_from_params(
        model=model,
        params=params,
        x=x,
        y=y,
        y_errors=y_errors,
        confidence_interval=confidence_interval,
        method=params.fit_method,
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
    method: Literal["trf", "dogbox"] = "trf",
) -> tuple[dict[str, float], dict[str, float]]:
    """Get fits and errors for project model."""
    fits, errors = fit(
        model=model,
        free_params=params.free_params,
        initial_values=params.values,
        model_bounds=params.bounds,
        x=x,
        y=y,
        y_errors=y_errors,
        confidence_interval=confidence_interval,
        method=method,
    )
    return (
        dict(zip(params.free_params, fits, strict=True)),
        dict(zip(params.free_errors, errors, strict=True)),
    )


def fit(
    model: Any,
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
        try:
            fits, pcov = curve_fit(
                f=model,
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
    if any(isnan(p) for p in params.values()):
        warn(
            "Cannot plot model fit with `nan` parameters.", RuntimeWarning, stacklevel=2
        )
        return
    if not ax:
        _fig, ax = plt.subplots()  # pyright: ignore[reportAssignmentType]
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
