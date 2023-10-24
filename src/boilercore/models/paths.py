"""Project paths."""

from pathlib import Path

from pydantic import DirectoryPath, FilePath

import boilercore
from boilercore import PROJECT_PATH
from boilercore.models import CreatePathsModel
from boilercore.paths import get_package_dir, map_stages


class Paths(CreatePathsModel):
    """Paths relevant to the project."""

    # * Roots
    project: DirectoryPath = PROJECT_PATH
    package: DirectoryPath = get_package_dir(boilercore)
    data: DirectoryPath = project / "data"
    stages: dict[str, FilePath] = map_stages(package / "stages", package)
    # * DVC deps
    fit: FilePath = package / "models/fit.py"
    # * DVC outs
    model: Path = data / "model.dillpickle"
    # * DVC-tracked inputs
    scripts: DirectoryPath = data / "scripts"
    # ? Files
    zotero: FilePath = scripts / "zotero.lua"
    filt: FilePath = scripts / "filt.py"
    csl: FilePath = scripts / "international-journal-of-heat-and-mass-transfer.csl"
    template: FilePath = scripts / "template.dotx"
