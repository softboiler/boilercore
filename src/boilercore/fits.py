"""Model fits."""

import warnings
from collections.abc import Mapping, Sequence
from functools import partial
from warnings import catch_warnings

import numpy as np
from scipy.optimize import OptimizeWarning, curve_fit

from boilercore.types import Bound, FitMethod, Guess


def fit_to_model(
    model_bounds: Mapping[str, Bound],
    initial_values: Mapping[str, Guess],
    free_params: list[str],
    fit_method: FitMethod,
    model,
    confidence_interval_95,
    x,
    y,
    y_errors,
    fixed_values,
):
    (bounds, guesses) = get_free_bounds_and_guesses(
        free_params, model_bounds, initial_values
    )

    # Perform fit, filling "nan" on failure or when covariance computation fails
    with catch_warnings():
        warnings.simplefilter("error", category=OptimizeWarning)
        try:
            fitted_params, pcov = curve_fit(
                partial(model, **fixed_values),
                x,
                y,
                sigma=y_errors,
                absolute_sigma=True,
                p0=guesses,
                bounds=tuple(
                    zip(*bounds, strict=True)
                ),  # Expects ([L1, L2, L3], [H1, H2, H3])
                method=fit_method,
            )
        except (RuntimeError, OptimizeWarning):
            dim = len(free_params)
            fitted_params = np.full(dim, np.nan)
            pcov = np.full((dim, dim), np.nan)

    # Compute confidence interval
    standard_errors = np.sqrt(np.diagonal(pcov))
    errors = standard_errors * confidence_interval_95

    # Catching `OptimizeWarning` should be enough, but let's explicitly check for inf
    fitted_params = np.where(np.isinf(errors), np.nan, fitted_params)
    errors = np.where(np.isinf(errors), np.nan, errors)
    return fitted_params, errors


def get_free_bounds_and_guesses(
    free_params: list[str],
    model_bounds: Mapping[str, Bound],
    initial_values: Mapping[str, Guess],
) -> tuple[Sequence[Bound], Sequence[Guess]]:
    """Given model bounds and initial values, return just the free parameter values.

    Returns a tuple of sequences of bounds and guesses required by the interface of
    `curve_fit`.
    """
    bounds = tuple(
        bound for param, bound in model_bounds.items() if param in free_params
    )
    guesses = tuple(
        guess for param, guess in initial_values.items() if param in free_params
    )

    return bounds, guesses
