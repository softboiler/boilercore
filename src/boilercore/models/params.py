"""Project parameters."""

from pathlib import Path

from pydantic.v1 import Field

from boilercore import get_params_file
from boilercore.models import SynchronizedPathsYamlModel
from boilercore.models.fit import Fit
from boilercore.models.geometry import Geometry
from boilercore.models.paths import Paths

PARAMS_FILE = get_params_file()


class Params(SynchronizedPathsYamlModel):
    """Global project parameters."""

    fit: Fit = Field(default_factory=Fit, description="Model fit parameters.")
    geometry: Geometry = Field(default_factory=Geometry, description="Geometry.")
    paths: Paths = Field(default_factory=Paths)

    def __init__(self, data_file: Path = PARAMS_FILE, **kwargs):
        super().__init__(data_file, **kwargs)


PARAMS = Params()
"""All project parameters, including paths."""
