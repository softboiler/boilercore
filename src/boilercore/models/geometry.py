"""Geometry."""

from typing import Annotated, TypeAlias

from pydantic import BaseModel, BeforeValidator, Field

from boilercore.types import Coupon, Rod

InchToMeterFloat: TypeAlias = Annotated[float, BeforeValidator(lambda v: v / 39.3701)]
"""A `float` initially in units of inches (in), but validates as meters (m)."""


class Geometry(BaseModel):
    """Geometry."""

    diameter: InchToMeterFloat = Field(
        default=0.375,  # (in)
        validate_default=True,
        description="(m) Common diameter of all rods.",
    )
    rods: dict[Rod, list[InchToMeterFloat]] = Field(
        default={  # (in)
            "X": [3.5253, 3.0500, 2.5756, 2.1006, 0.3754],
            "Y": [3.5250, 3.0504, 2.5752, 2.1008, 0.3752],
            "R": [4.1000, 3.6250, 3.1500, 2.6750, 0.9500],
            "W": [3.5250, 3.0500, 2.5750, 2.1000, 0.3750],
        },
        validate_default=True,
        description="(m) Distance of each thermocouple from the cool side of the rod, starting with TC1. Fifth thermocouple may be omitted.",
    )
    coupons: dict[Coupon, InchToMeterFloat] = Field(
        default={  # (in)
            "A0": 0.000,
            "A1": 0.766,
            "A2": 0.770,
            "A3": 0.769,
            "A4": 0.746,
            "A5": 0.734,
            "A6": 0.750,
            "A7": 0.753,
            "A8": 0.753,
            "A9": 0.553,
        },
        validate_default=True,
        description="(m) Length of the coupon.",
    )


GEOMETRY = Geometry()
"""Geometry."""
