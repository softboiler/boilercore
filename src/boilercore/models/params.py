"""Project parameters."""

from pathlib import Path

from pydantic import Field

from boilercore import PROJECT_PATH
from boilercore.fits import Fit
from boilercore.models import SynchronizedPathsYamlModel
from boilercore.models.geometry import Geometry
from boilercore.models.paths import Paths


class Params(SynchronizedPathsYamlModel):
    """Global project parameters."""

    fit: Fit = Field(default_factory=Fit, description="Model fit parameters.")
    geometry: Geometry = Field(default_factory=Geometry, description="Geometry.")
    paths: Paths

    def __init__(
        self,
        data_file: Path = PROJECT_PATH / Path("params.yaml"),
        root: Path = PROJECT_PATH,
    ):
        super().__init__(data_file, paths=Paths(root=root.resolve()))


PARAMS = Params()
"""All project parameters, including paths."""
