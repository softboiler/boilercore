"""Test configuration."""

from pathlib import Path
from types import SimpleNamespace

import pytest
import seaborn as sns

from boilercore.modelfun import fix_model, get_model
from boilercore.testing import get_nb_client, get_nb_namespace

MODELFUN = Path("src/boilercore/stages/modelfun.ipynb")


@pytest.fixture(scope="module")
def ns() -> SimpleNamespace:
    """Namespace for the model function notebook."""
    return get_nb_namespace(get_nb_client(MODELFUN))


@pytest.fixture(scope="module")
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
