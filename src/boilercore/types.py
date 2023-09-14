"""Types."""

from typing import Literal, TypeVar

Bound = TypeVar("Bound", bound=tuple[float | str, float | str])
"""Boundary for a parameter to be fitted."""

Guess = TypeVar("Guess", bound=float)
"""Guess for a parameter to be fitted."""

FitMethod = Literal["lm", "trf", "dogbox"]
"""Valid methods for curve fitting."""

Coupon = Literal["A0", "A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9"]
"""The coupon attached to the rod for this trial."""

Rod = Literal["W", "X", "Y", "R"]
"""The rod used in this trial."""

Group = Literal["control", "porous", "hybrid"]
"""The group that this sample belongs to."""

Joint = Literal["paste", "epoxy", "solder", "none"]
"""The method used to join parts of the sample in this trial."""

Sample = Literal["B3"]
"""The sample attached to the coupon in this trial."""
