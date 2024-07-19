"""Test model function and model fit."""

import pytest
from numpy import allclose, array, linspace, sqrt
from sympy import Eq

from boilercore.fits import fit_and_plot
from boilercore.testing import MFParam
from boilercore_tests.modelfun import FIT


def approx(*args):
    """Approximate equality with a relative tolerance of 1e-3."""
    return pytest.approx(*args, rel=0.001, abs=0.01)


@pytest.mark.parametrize("group_name", ["params", "intermediate_vars", "functions"])
def test_syms(group_name: str):
    """Test that declared symbolic variables are assigned to the correct symbols."""
    from boilercore import syms  # noqa: PLC0415

    module_vars = vars(syms)
    sym_group = module_vars[group_name]
    symvars = {
        var: sym
        for var, sym in module_vars.items()
        if var in [group_sym.name for group_sym in sym_group]
    }
    assert all(var == sym.name for var, sym in symvars.items())


@pytest.mark.slow()
def test_forward_model(model):
    """Test that the model evaluates to the expected output for known input."""
    # fmt: off
    assert allclose(
        model(x=linspace(0, 0.10), **FIT.values),
        array([
            105.00000000, 106.02041984, 107.04086600, 108.06134295,
            109.08185515, 110.10240706, 111.12300315, 112.14364787,
            113.16434569, 114.18510108, 115.20591849, 116.22680239,
            117.24775725, 118.26878752, 119.28989768, 120.31109218,
            121.33237550, 122.35375209, 123.37522643, 124.39682095,
            125.41877670, 126.44117155, 127.46400996, 128.48729641,
            129.51103538, 130.53523133, 131.55988875, 132.58501211,
            133.61060591, 134.63667462, 135.66322273, 136.69025473,
            137.71777511, 138.74578836, 139.77429898, 140.80331147,
            141.83283032, 142.86286004, 143.89340514, 144.92447011,
            145.95605946, 146.98817771, 148.02082937, 149.05401896,
            150.08775099, 151.12202998, 152.15686045, 153.19224694,
            154.22819396, 155.26470605
        ]),
    )


# TODO: Add `nan` failed fit check
@pytest.mark.slow()
@pytest.mark.usefixtures("plt")
@pytest.mark.parametrize(
    ("run", "y", "expected"),
    [
        pytest.param(
            *MFParam(
                run=(id_ := "low"),  # Run: 2022-09-14T10:21:00
                y=[94.00, 94.00, 94.00, 94.00, 94.00],
                expected={"T_s": 94.00, "q_s": 89.32, "h_a": 0.001},
            ),
            id=id_,
        ),
        pytest.param(
            *MFParam(
                run=(id_ := "med"),  # Run: 2022-09-14T12:09:46
                y=[108.00, 106.20, 105.50, 104.40, 102.00],
                expected={"T_s": 100.98, "q_s": 16774.20, "h_a": 13.72},
            ),
            id=id_,
        ),
        pytest.param(
            *MFParam(
                run=(id_ := "high"),  # Run: 2022-09-14 15:17:21
                y=[165.7, 156.8, 149.2, 141.1, 116.4],
                expected={"T_s": 103.37, "q_s": 216022.56, "h_a": 23.38},
            ),
            id=id_,
        ),
    ],
)
def test_model_fit(params, model, run, y, expected):
    """Test that the model fit is as expected."""
    x = params.geometry.rods["R"]
    y_errors = array([2.2] * 5) / sqrt(100)
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
