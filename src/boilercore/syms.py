"""Symbolic parameter groups for model fitting."""

from sympy import Function, symbols

params = symbols([
    "x",
    "T_s",
    "q_s",
    "h_a",
    "h_w",
    "r",
    "T_infa",
    "T_infw",
    "x_s",
    "x_wa",
    "k",
])
(
    x,  # (m) Independent variable
    T_s,  # (C) Surface temperature of the sample rod at the boiling surface
    q_s,  # (W/m^2) Heat flux at the water-side surface of the sample rod
    h_a,  # (W/m^2-K) Radial convection heat transfer coefficient outside the water
    h_w,  # (W/m^2-K) Radial convection heat transfer coefficient in the water
    r,  # (m) Radius of the sample rod
    T_infa,  # (C) Ambient temperature
    T_infw,  # (C) Water-side ambient temperature
    x_s,  # (m) Coordinate of boiling surface of the sample rod
    x_wa,  # (m) Coordinate of chamber floor, with water in the chamber and air outside
    k,  # (W/m-K) Thermal conductivity of the sample rod
) = params

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
    q_0,  # (W/m^2) Heat flux at origin of a general domain
    q_wa,  # (W/m^2) Heat flux at the water-air domain interface
    T_0,  # (C) Temperature at origin of a general domain
    T_inf,  # (C) Ambient temperature
    T_wa,  # (C) Temperature at water-air domain interface
    x_0,  # (m) Origin of a general domain
) = intermediate_vars

functions = symbols(
    """
    T*,
    T_a,
    T_w,
    T,
    """,
    cls=Function,  # pyright: ignore[reportArgumentType]
)
(
    T_int,  # (T*, K) The general solution to the ODE
    T_a,  # (C) Solution in air
    T_w,  # (C) Solution in water
    T,  # (C) The piecewise combination of the two above solutions
) = functions
