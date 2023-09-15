"""Fit parameters."""

from typing import Literal, TypeAlias

import numpy as np
from pydantic import BaseModel, Field, validator

EPS = float(np.finfo(float).eps)
MIN_NZ = EPS
LB_MIN = EPS
H_MIN = LB_MIN  # (W/m^2-K)
FIT_METHOD = "trf"
MODEL_PARAMS = ["T_s", "q_s", "k", "h_a", "h_w"]
FIXED_PARAMS = ["k", "h_w"]


def get_model_errors(params: list[str]) -> list[str]:
    return [f"{param}_err" for param in params]


Bound: TypeAlias = float | Literal["-inf", "inf"]


class Fit(BaseModel):
    """Parameters for model fit."""

    fit_method = "trf"
    """Model fit method."""
    model_params = MODEL_PARAMS
    """Parameters that can vary in the model. Some will be fixed."""
    fixed_params = FIXED_PARAMS
    """Parameters to fix. Evaluated before fitting, overridable in code."""
    free_params = [param for param in MODEL_PARAMS if param not in FIXED_PARAMS]
    """Free parameters."""
    free_errors = get_model_errors(free_params)
    model_errors = get_model_errors(model_params)
    fixed_errors = get_model_errors(fixed_params)
    params_and_errors = [*model_params, *model_errors]

    model_inputs: dict[str, float] = Field(
        default=dict(
            r=0.0047625,  # (m)
            T_infa=25.0,  # (C)
            T_infw=100.0,  # (C)
            x_s=0.0,  # (m)
            x_wa=0.0381,  # (m)
        ),
        description="Inputs to the symbolic model float evaluation stage.",
    )

    # ! MODEL BOUNDS

    model_bounds: dict[str, tuple[Bound, Bound]] = Field(
        default=dict(
            T_s=(-273.0, "inf"),  # (C) T_s
            q_s=("-inf", "inf"),  # (W/m^2) q_s
            k=(LB_MIN, "inf"),  # (W/m-K) k
            h_a=(LB_MIN, "inf"),  # (W/m^2-K) h_a
            h_w=(LB_MIN, "inf"),  # (W/m^2-K) h_w
        ),
        description="Bounds for the model parameters. Not used if parameter is fixed.",
    )

    @validator("model_bounds", always=True)
    def validate_model_bounds(cls, model_bounds) -> dict[str, tuple[float, float]]:
        """Substitute np.inf for 'inf' and avoid exact zero lower bounds."""
        for param, b in model_bounds.items():
            if isinstance(b[0], str) and "-inf" in b[0]:
                b0 = -np.inf
            elif b[0] == 0.0:
                b0 = MIN_NZ
            else:
                b0 = b[0]
            b1 = np.inf if isinstance(b[0], str) and "inf" in b[1] else b[1]
            model_bounds[param] = (b0, b1)
        return model_bounds

    # ! INITIAL VALUES

    initial_values: dict[str, float] = Field(
        default=dict(
            T_s=100.0,  # (C)
            q_s=10.0,  # (W/cm^2)
            k=400.0,  # (W/m-K)
            h_a=H_MIN,  # (W/m^2-K)
            h_w=H_MIN,  # (W/m^2-K)
        ),
        description="Initial guess for free parameters, constant value otherwise.",
    )

    @validator("initial_values", always=True)
    def validate_initial_values(cls, model_inputs) -> dict[str, float]:
        """Avoid exact zero guesses."""
        return {param: MIN_NZ if v == 0.0 else v for param, v in model_inputs.items()}

    @property
    def fixed_values(self) -> dict[str, float]:
        """Fixed parameter values."""
        return {k: v for k, v in self.initial_values.items() if k in self.fixed_params}


FIT = Fit()
"""Fit parameters."""
