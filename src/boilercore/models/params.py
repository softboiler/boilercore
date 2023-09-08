"""Project parameters."""

from typing import Literal, TypeAlias

import numpy as np
from pydantic import BaseModel, Extra, Field, validator

from boilercore.types import FitMethod

Bound: TypeAlias = float | Literal["-inf", "inf"]


class FitParams(BaseModel, extra=Extra.allow):
    """Parameters for model fit."""

    fit_method: FitMethod = Field(default="trf", description="Model fit method.")
    model_params: list[str] = Field(
        default=["T_s", "q_s", "k", "h_a", "h_w"],
        description="Parameters that can vary in the model. Some will be fixed.",
    )
    model_inputs: dict[str, float] = Field(
        default=dict(
            r=0.0047625,  # (m)
            T_infa=25.0,  # (C)
            T_infw=100.0,  # (C)
            x_s=0,  # (m)
            x_wa=0.0381,  # (m)
        ),
        description="Inputs to the symbolic model float evaluation stage.",
    )

    # ! MODEL BOUNDS

    model_bounds: dict[str, tuple[Bound, Bound]] = Field(
        default=dict(
            T_s=(95, "inf"),  # (C) T_s
            q_s=(0, "inf"),  # (W/m^2) q_s
            k=(350, 450),  # (W/m-K) k
            h_a=(0, "inf"),  # (W/m^2-K) h_a
            h_w=(0, "inf"),  # (W/m^2-K) h_w
        ),
        description="Bounds for the model parameters. Not used if parameter is fixed.",
    )

    @validator("model_bounds", always=True)
    def validate_model_bounds(cls, model_bounds) -> dict[str, tuple[float, float]]:
        """Substitute inf for np.inf."""
        for param, b in model_bounds.items():
            b0 = -np.inf if isinstance(b[0], str) and "-inf" in b[0] else b[0]
            b1 = np.inf if isinstance(b[0], str) and "inf" in b[1] else b[1]
            model_bounds[param] = (b0, b1)
        return model_bounds

    # ! FIXED PARAMS

    fixed_params: list[str] = Field(
        default=["k", "h_w"],
        description="Parameters to fix. Evaluated before fitting, overridable in code.",
    )

    @validator("fixed_params", always=True, each_item=True)
    def validate_each_fixed_param(cls, param, values):
        """Check that the fixed parameter is one of the model parameters."""
        if param in values["model_params"]:
            return param
        raise ValueError(f"Fixed parameter {param} not in model parameters")

    # ! INITIAL VALUES

    initial_values: dict[str, float] = Field(
        default=dict(
            T_s=95,  # (C) T_s
            q_s=0,  # (W/m^2) q_s
            k=400,  # (W/m-K) k
            h_a=0,  # (W/m^2-K) h_a
            h_w=0,  # (W/m^2-K) h_w
        ),
        description="Initial guess for free parameters, constant value otherwise.",
    )

    @validator("initial_values", always=True)
    def validate_initial_values(cls, model_inputs) -> dict[str, float]:
        """Avoid division by zero in select parameters."""
        eps = float(np.finfo(float).eps)
        params_to_check = ["h_a", "h_w"]
        return {
            param: eps if v == 0 and param in params_to_check else v
            for param, v in model_inputs.items()
        }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.free_params = [p for p in self.model_params if p not in self.fixed_params]
        self.free_errors = self.get_model_errors(self.free_params)
        self.model_errors = self.get_model_errors(self.model_params)
        self.fixed_errors = self.get_model_errors(self.fixed_params)
        self.params_and_errors = self.model_params + self.model_errors
        self.fixed_values = {
            k: v for k, v in self.initial_values.items() if k in self.fixed_params
        }

    def get_model_errors(self, params) -> list[str]:
        return [f"{param}_err" for param in params]
