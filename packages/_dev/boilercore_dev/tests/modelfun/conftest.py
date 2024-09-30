"""Test configuration."""

from pathlib import Path
from types import SimpleNamespace

import pytest
import seaborn as sns

from boilercore.notebooks.namespaces import get_nb_ns
from boilercore_dev.tests.modelfun import FIT

MODELFUN = Path("src/boilercore/stages/modelfun.ipynb").resolve()


@pytest.fixture
def ns() -> SimpleNamespace:
    """Namespace for the model function notebook."""
    return get_nb_ns(MODELFUN.read_text(encoding="utf-8"))


@pytest.fixture
def model(params):
    """Deserialized model."""
    return FIT.get_models(params.paths.models)[1]


@pytest.fixture
def plt(plt):
    """Plot."""
    sns.set_theme(
        context="notebook", style="whitegrid", palette="bright", font="sans-serif"
    )
    yield plt
    plt.saveas = f"{plt.saveas[:-4]}.png"
