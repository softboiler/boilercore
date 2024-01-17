"""Test basic parameter models."""

from pathlib import Path

import pytest
from boilercore.models import DefaultPathsModel, SynchronizedPathsYamlModel, YamlModel
from pydantic.v1 import DirectoryPath, Field

from boilercore_tests.models import VarietyOfPaths


@pytest.mark.parametrize(
    "chdir", [pytest.param(True, id="chdir"), pytest.param(False, id="nochdir")]
)
@pytest.mark.parametrize("yamlmodel", [YamlModel, SynchronizedPathsYamlModel])
def test_model_combinations(
    paths_and_model: tuple[VarietyOfPaths, type[DefaultPathsModel]],
    yamlmodel: type[YamlModel],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    chdir: bool,
):
    """Test combinations of paths, models, and field types."""
    (path_, path_sequence_, path_mapping_, file_), pathsmodel = paths_and_model

    class Paths(pathsmodel):
        path: DirectoryPath = path_
        field_path: DirectoryPath = Field(default=path_)
        path_sequence: tuple[DirectoryPath, ...] = path_sequence_
        field_path_sequence: tuple[DirectoryPath, ...] = Field(default=path_sequence_)
        path_mapping: dict[str, DirectoryPath] = path_mapping_
        field_path_mapping: dict[str, DirectoryPath] = Field(default=path_mapping_)
        file: Path = file_
        field_file: Path = Field(default=file_)

    class Params(yamlmodel):
        paths: Paths = Field(default_factory=Paths)
        field_paths: Paths = Paths()

        def __init__(self):
            super().__init__(tmp_path / "params.yaml")

    if chdir:
        with monkeypatch.context() as m:
            m.chdir(tmp_path)
            Params()
    else:
        Params()
