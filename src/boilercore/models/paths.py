"""Project paths."""

from pathlib import Path

from pydantic import DirectoryPath, FilePath

import boilercore
from boilercore.models import CreatePathsModel
from boilercore.paths import get_package_dir, map_stages


class Paths(CreatePathsModel):
    """Paths relevant to the project."""

    # * Roots
    package: DirectoryPath = get_package_dir(boilercore)
    data: DirectoryPath = Path("data")
    stages: dict[str, FilePath] = map_stages(
        package / "stages", suffixes=[".py", ".ipynb"]
    )

    # * DVC-tracked inputs
    # ! Scripts
    scripts: DirectoryPath = data / "scripts"
    filt: FilePath = scripts / "filt.py"
    csl: FilePath = scripts / "international-journal-of-heat-and-mass-transfer.csl"
    template: FilePath = scripts / "template.dotx"

    # * DVC-tracked results
    models: DirectoryPath = data / "models"
