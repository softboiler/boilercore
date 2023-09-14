from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
from matplotlib import pyplot as plt
from uncertainties import ufloat

MEASUREMENTS_COLOR = (0.2, 0.2, 0.2)


def plot_fit(
    ax: plt.Axes,
    run: str,
    x: Sequence[Any],
    y: Sequence[Any],
    y_errors: Sequence[Any],
    y_0: float,
    model: Any,
    params: Mapping[str, Any],
    errors: Mapping[str, Any],
    measurements_color: tuple[float, float, float] = MEASUREMENTS_COLOR,
):
    """Plot the model fit for a run."""

    # Plot setup
    ax.margins(0, 0)
    ax.set_title(f"{run = }")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("T (C)")

    # Initial plot boundaries
    x_bounds = np.array([0, x[-1]])
    y_bounds = model(x_bounds, **params)
    ax.plot(x_bounds, y_bounds, "none")

    # Measurements
    ax.plot(x, y, ".", label="Measurements", color=measurements_color, markersize=10)
    (xlim_min, xlim_max) = ax.get_xlim()
    pad = 0.025 * (xlim_max - xlim_min)
    x_smooth = np.linspace(xlim_min - pad, xlim_max + pad, 200)
    y_smooth, y_min, y_max = get_model_with_error(model, x_smooth, params, errors)
    ax.plot(x_smooth, y_smooth, "--", label="Model Fit")

    # Error
    ax.errorbar(x=x, y=y, yerr=y_errors, fmt="none", color=measurements_color)  # type: ignore
    ax.fill_between(
        x=x_smooth,
        y1=y_min,  # type: ignore
        y2=y_max,  # type: ignore
        color=[0.8, 0.8, 0.8],
        edgecolor=[1, 1, 1],
        label="95% CI",
    )
    ax.legend()

    # Extrapolation
    ax.plot(0, y_0, "x", label="Extrapolation", color=[1, 0, 0])

    # Finishing
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
