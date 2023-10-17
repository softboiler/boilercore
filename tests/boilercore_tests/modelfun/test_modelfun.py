"""Test model function and model fit."""

import numpy as np
import pytest
from sympy import Eq

from boilercore.fits import fit_and_plot
from boilercore.models.fit import FIT
from boilercore.testing import MFParam


def approx(*args):
    """Approximate equality with a relative tolerance of 1e-3."""
    return pytest.approx(*args, rel=0.001, abs=0.01)


@pytest.mark.parametrize(
    "group_name", ["params", "inputs", "intermediate_vars", "functions"]
)
def test_syms(group_name: str):
    """Test that declared symbolic variables are assigned to the correct symbols."""
    from boilercore import syms

    module_vars = vars(syms)
    sym_group = module_vars[group_name]
    symvars = {
        var: sym
        for var, sym in module_vars.items()
        if var in [group_sym.name for group_sym in sym_group]
    }
    assert all(var == sym.name for var, sym in symvars.items())


@pytest.mark.slow()
def test_forward_model(nb_model):
    """Test that the model evaluates to the expected output for known input."""
    # fmt: off
    assert np.allclose(
        nb_model(
            x=np.linspace(0, 0.10),
            T_s=105,  # (C)
            q_s=20,  # (W/cm^2)p
            h_a=100,  # (W/m^2-K)
            h_w=np.finfo(float).eps,  # (W/m^2-K)
            k=400,  # (W/m-K)
        ),
        np.array(
            [
                105.        , 106.02040672, 107.04081917, 108.06122589,
                109.08163071, 110.10204124, 111.12244987, 112.14286041,
                113.16326523, 114.18367195, 115.2040844 , 116.22449112,
                117.24489594, 118.26530647, 119.2857151 , 120.30612183,
                121.32653046, 122.34693718, 123.36734962, 124.39013155,
                125.4467062 , 126.5472041 , 127.69210646, 128.88191394,
                130.11714679, 131.39834518, 132.72606933, 134.10089984,
                135.52343788, 136.99430552, 138.51414591, 140.08362367,
                141.70342508, 143.37425846, 145.09685442, 146.87196622,
                148.70037008, 150.58286552, 152.52027572, 154.51344787,
                156.56325353, 158.67058905, 160.83637592, 163.06156119,
                165.3471179 , 167.69404545, 170.10337013, 172.57614547,
                175.11345277, 177.71640154
            ]
        ),
    )


@pytest.mark.slow()
@pytest.mark.usefixtures("plt")
@pytest.mark.parametrize(
    ("run", "y", "expected"),
    [
        pytest.param(
            *MFParam(
                run=(id_ := "low"),  # Run: 2022-09-14T10:21:00
                y=[93.91, 93.28, 94.48, 94.84, 96.30],
                expected={"T_s": 97.26, "q_s": -1.57, "h_a": 2.75},
            ),
            id=id_,
        ),
        pytest.param(
            *MFParam(
                run=(id_ := "med"),  # Run: 2022-09-14T12:09:46
                y=[108.00, 106.20, 105.50, 104.40, 102.00],
                expected={"T_s": 100.98, "q_s": 1.69, "h_a": 13.64},
            ),
            id=id_,
        ),
        pytest.param(
            *MFParam(
                run=(id_ := "high"),  # Run: 2022-09-14 15:17:21
                y=[165.7, 156.8, 149.2, 141.1, 116.4],
                expected={"T_s": 103.37, "q_s": 21.60, "h_a": 23.38},
            ),
            id=id_,
        ),
    ],
)
def test_model_fit(params, model, run, y, expected):
    """Test that the model fit is as expected."""
    x = params.geometry.rods["R"]
    y_errors = np.array([*[2.2] * 4, *[1.0]]) / np.sqrt(10)
    result, _ = fit_and_plot(
        model=model, params=FIT, x=x, y=y, y_errors=y_errors, run=run
    )
    assert result == approx(expected)


@pytest.mark.slow()
def test_ode(ns):
    """Verify the solution to the ODE by substitution."""
    # Don't subs/simplify the lhs then try equating to zero. Doesn't work. "Truth value of
    # relational" issue. Here we subs/simplify the whole ODE equation.
    ode, T, x, T_int_expr = ns.ode, ns.T, ns.x, ns.T_int_expr  # noqa: N806
    assert ode.subs(T(x), T_int_expr).simplify()


@pytest.mark.slow()
def test_temperature_continuous(ns):
    """Test that temperature is continuous at the domain transition."""
    T_wa_expr_w, T_wa_expr_a = ns.T_wa_expr_w, ns.T_wa_expr_a  # noqa: N806
    assert Eq(T_wa_expr_w, T_wa_expr_a).simplify()


@pytest.mark.slow()
def test_temperature_gradient_continuous(ns):
    """Test that the temperature gradient is continuous at the domain transition."""
    q_wa_expr_w, q_wa_expr_a = ns.q_wa_expr_w, ns.q_wa_expr_a
    assert Eq(q_wa_expr_w, q_wa_expr_a).simplify()
