"""Test configuration."""

from pathlib import Path
from types import SimpleNamespace

import pytest
import seaborn as sns

from boilercore.modelfun import fix_model, get_model
from boilercore.notebooks.namespaces import get_nb_ns

MODELFUN = Path("src/boilercore/stages/modelfun.ipynb")


@pytest.fixture()
def ns(request) -> SimpleNamespace:
    """Namespace for the model function notebook."""
    return get_nb_ns(MODELFUN.read_text(encoding="utf-8"))


@pytest.fixture()
def nb_model(ns):
    """Notebook model."""
    return fix_model(ns.models.for_ufloat)


@pytest.fixture()
def model(params):
    """Deserialized model."""
    _, model = get_model(params.paths.model)
    return model


@pytest.fixture()
def plt(plt):
    """Plot."""
    sns.set_theme(
        context="notebook", style="whitegrid", palette="bright", font="sans-serif"
    )
    yield plt
    plt.saveas = f"{plt.saveas[:-4]}.png"
