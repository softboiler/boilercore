"""Test basic parameter models."""

from pathlib import Path

import pytest
from pydantic import DirectoryPath, Field, FilePath

from boilercore.models import (
    CreatePathsModel,
    DefaultPathsModel,
    SynchronizedPathsYamlModel,
)


@pytest.mark.parametrize("pathsmodel", [DefaultPathsModel, CreatePathsModel])
@pytest.mark.parametrize(
    "chdir", [pytest.param(True, id="chdir"), pytest.param(False, id="nochdir")]
)
def test_model_combinations(
    pathsmodel: type[DefaultPathsModel],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    chdir: bool,
):
    """Test combinations of paths, models, and field types."""
    # sourcery skip: no-conditionals-in-tests
    # sourcery skip: no-loop-in-tests
    path_ = tmp_path / "directory"
    path_sequence_ = tuple(tmp_path / path for path in ["a", "b", "c"])
    path_mapping_ = {f"{i}": path for i, path in enumerate(path_sequence_)}
    file_ = tmp_path / "file.txt"
    if pathsmodel is DefaultPathsModel:
        for p in [path_, *list(path_sequence_)]:
            p.mkdir()
        file_.touch()

    class Paths(pathsmodel):
        root: DirectoryPath = tmp_path
        path: DirectoryPath = path_
        field_path: DirectoryPath = Field(default=path_)
        path_sequence: tuple[DirectoryPath, ...] = path_sequence_
        field_path_sequence: tuple[DirectoryPath, ...] = Field(default=path_sequence_)
        path_mapping: dict[str, DirectoryPath] = path_mapping_
        field_path_mapping: dict[str, DirectoryPath] = Field(default=path_mapping_)
        file: Path = file_
        field_file: Path = Field(default=file_)

    class Params(SynchronizedPathsYamlModel):
        source: FilePath = tmp_path / "params.yaml"
        paths: Paths = Field(default_factory=Paths)

    if chdir:
        with monkeypatch.context() as m:
            m.chdir(tmp_path)
            Params()
    else:
        Params()
