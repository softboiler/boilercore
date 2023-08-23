"""Types used throughout this package."""

from typing import Literal, TypeVar

Bound = TypeVar("Bound", bound=tuple[float | str, float | str])
"""Boundary for a parameter to be fitted."""

Guess = TypeVar("Guess", bound=float)
"""Guess for a parameter to be fitted."""

FitMethod = Literal["lm", "trf", "dogbox"]
"""Valid methods for curve fitting."""
