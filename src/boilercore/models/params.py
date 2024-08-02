"""Project parameters."""

from pathlib import Path

from pydantic import Field, FilePath

from boilercore.fits import Fit
from boilercore.models import SynchronizedPathsYamlModel
from boilercore.models.geometry import Geometry
from boilercore.models.paths import PackagePaths, Paths


class Params(SynchronizedPathsYamlModel):
    """Global project parameters."""

    source: FilePath = Path.cwd() / "params.yaml"
    fit: Fit = Field(default_factory=Fit, description="Model fit parameters.")
    geometry: Geometry = Field(default_factory=Geometry, description="Geometry.")
    paths: Paths = Field(default_factory=Paths)
    package_paths: PackagePaths = Field(default_factory=PackagePaths)
