"""Project parameters."""

from pathlib import Path

from pydantic import Field

from boilercore.fits import Fit
from boilercore.models import SynchronizedPathsYamlModel
from boilercore.models.geometry import Geometry
from boilercore.models.paths import Paths


class Params(SynchronizedPathsYamlModel):
    """Global project parameters."""

    fit: Fit = Field(default_factory=Fit, description="Model fit parameters.")
    geometry: Geometry = Field(default_factory=Geometry, description="Geometry.")
    paths: Paths

    def __init__(self, root: Path | None = None, data_file: Path | None = None):
        root = (root or Path.cwd()).resolve()
        data_file = data_file or root / "params.yaml"
        super().__init__(data_file, paths=Paths(root=root))
