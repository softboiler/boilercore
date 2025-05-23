"""Project paths."""

from pathlib import Path

from pydantic import DirectoryPath, FilePath

import boilercore
from boilercore.models import CreatePathsModel, DefaultPathsModel
from boilercore.paths import get_package_dir, map_stages


class Paths(CreatePathsModel):
    """Paths relevant to the project."""

    root: DirectoryPath = Path.cwd() / "data"
    # * DVC-tracked results
    models: DirectoryPath = root / "models"


class PackagePaths(DefaultPathsModel):
    """Package paths."""

    root: DirectoryPath = get_package_dir(boilercore)
    stages: dict[str, FilePath] = map_stages(
        root / "stages", suffixes=[".py", ".ipynb"]
    )
