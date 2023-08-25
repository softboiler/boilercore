from pathlib import Path

import pytest
from pydantic import DirectoryPath, Field

from boilercore.models import (
    CreatePathsModel,
    DefaultPathsModel,
    SynchronizedPathsYamlModel,
    YamlModel,
)
from tests import VarietyOfPaths


@pytest.fixture(params=[DefaultPathsModel, CreatePathsModel])
def paths_and_model(
    request: pytest.FixtureRequest, tmp_path: Path
) -> tuple[VarietyOfPaths, type[DefaultPathsModel]]:
    path = tmp_path / "directory"
    path_sequence = tuple(tmp_path / path for path in ["a", "b", "c"])
    path_mapping = {f"{i}": path for i, path in enumerate(path_sequence)}
    file = tmp_path / "file.txt"
    if request.param is DefaultPathsModel:
        for p in [path, *list(path_sequence)]:
            p.mkdir()
        file.touch()
    return (path, path_sequence, path_mapping, file), request.param


@pytest.fixture(params=[DefaultPathsModel, CreatePathsModel])
def pathsmodel(
    request: pytest.FixtureRequest, tmp_path: Path
) -> type[DefaultPathsModel]:
    path_ = tmp_path / "directory"
    path_sequence_ = tuple(tmp_path / path for path in ["a", "b", "c"])
    path_mapping_ = {f"{i}": path for i, path in enumerate(path_sequence_)}
    file_ = tmp_path / "file.txt"

    class Paths(request.param):
        tmp_path_: DirectoryPath = tmp_path
        path: DirectoryPath = path_
        field_path: DirectoryPath = Field(default=path_)
        path_sequence: tuple[DirectoryPath, ...] = path_sequence_
        field_path_sequence: tuple[DirectoryPath, ...] = Field(default=path_sequence_)
        path_mapping: dict[str, DirectoryPath] = path_mapping_
        field_path_mapping: dict[str, DirectoryPath] = Field(default=path_mapping_)
        file: Path = file_
        field_file: Path = Field(default=file_)

    if isinstance(Paths, DefaultPathsModel):
        for path in [path_, *list(path_sequence_)]:
            path.mkdir()
        file_.touch()

    return Paths


@pytest.fixture(params=[YamlModel, SynchronizedPathsYamlModel])
def yamlmodel(
    request: pytest.FixtureRequest, pathsmodel: type[DefaultPathsModel]
) -> type[DefaultPathsModel]:
    tmp_path = pathsmodel.__fields__["tmp_path_"].default

    class Params(request.param):
        paths: DefaultPathsModel = Field(default_factory=pathsmodel)

        def __init__(self):
            super().__init__(tmp_path / "params.yaml")

    return Params
