"""Symbolic parameter groups for model fitting."""

from sympy import Function, symbols

from boilercore.models.fit import FIT

params = symbols(["x", *FIT.free_params, *FIT.fixed_params])
(x, T_s, q_s, h_a, k, h_w) = params

inputs = symbols(list(FIT.model_inputs.keys()))
(r, T_infa, T_infw, x_s, x_wa) = inputs

intermediate_vars = symbols(
    """
    h,
    q_0,
    q_wa,
    T_0,
    T_inf,
    T_wa,
    x_0,
    """
)
(
    h,  # (W/m^2-K) Convection heat transfer coefficient
    q_0,  # (W/m^2) q at x_0, the LHS of a general domain
    q_wa,  # (W/m^2) q at the domain interface
    T_0,  # (C) T at x_0, the LHS of a general domain
    T_inf,  # (C) Ambient temperature
    T_wa,  # (C) T at the domain interface
    x_0,  # (m) x at the LHS of a general domain
) = intermediate_vars

functions = symbols(
    """
    T*,
    T_a,
    T_w,
    T,
    """,
    cls=Function,  # type: ignore  # sympy
)
(
    T_int,  # (T*, C) The general solution to the ODE
    T_a,  # (C) Solution in air
    T_w,  # (C) Solution in water
    T,  # (C) The piecewise combination of the two above solutions
) = functions
