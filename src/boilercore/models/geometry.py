"""Geometry."""

import numpy as np
from pydantic.v1 import BaseModel, Field, validator

from boilercore.types import Coupon, Rod


class Geometry(BaseModel):
    """The fixed geometry for the problem."""

    # Prefix with underscore to exclude from schema
    _in_p_m: float = 39.3701  # (in/m) Conversion factor

    # ! DIAMETER

    diameter: float = Field(
        default=0.375, description="The common diameter of all rods."
    )

    @validator("diameter", always=True)
    @classmethod
    def validate_diameter(cls, diameter):
        """Convert from inches to meters."""
        return diameter / cls._in_p_m

    # ! RODS

    rods: dict[Rod, list[float]] = Field(
        default={
            "X": [3.5253, 3.0500, 2.5756, 2.1006, 0.3754],
            "Y": [3.5250, 3.0504, 2.5752, 2.1008, 0.3752],
            "R": [4.1000, 3.6250, 3.1500, 2.6750, 0.9500],
            "W": [3.5250, 3.0500, 2.5750, 2.1000, 0.3750],
        },
        description="Distance of each thermocouple from the cool side of the rod, starting with TC1. Fifth thermocouple may be omitted. Input: inch. Output: meter.",
    )

    @validator("rods", pre=True, always=True)
    @classmethod
    def validate_rods(cls, rods):
        """Convert from inches to meters."""
        return {
            rod: list(np.array(values) / cls._in_p_m) for rod, values in rods.items()
        }

    # ! COUPONS

    coupons: dict[Coupon, float] = Field(
        default={
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
        description="Length of the coupon. Input: inch. Output: meter.",
    )

    @validator("coupons", pre=True, always=True)
    @classmethod
    def validate_coupons(cls, coupons):
        """Convert from inches to meters."""
        return {coupon: value / cls._in_p_m for coupon, value in coupons.items()}


GEOMETRY = Geometry()
