"""Basic models."""

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, get_origin

from pydantic.v1 import BaseModel, validator
from ruamel.yaml import YAML

from boilercore.models.types import PathOrPaths, Paths

YAML_INDENT = 2
yaml = YAML()
yaml.indent(mapping=YAML_INDENT, sequence=YAML_INDENT, offset=YAML_INDENT)
yaml.width = 1000  # Otherwise Ruamel breaks lines illegally
yaml.preserve_quotes = True


class YamlModel(BaseModel):
    """Model of a YAML file with automatic schema generation.

    Updates a JSON schema next to the YAML file with each initialization.
    """

    def __init__(self, data_file: Path, **kwargs):
        """Initialize and update the schema."""
        self.update_schema(data_file)
        params = self.get_params(data_file)
        super().__init__(**(params | kwargs))

    def get_params(self, data_file: Path) -> dict[str, Any]:
        """Get parameters from file."""
        return yaml.load(data_file) or {} if data_file.exists() else {}

    def update_schema(self, data_file: Path):
        """Update the schema file next to the data file."""
        schema_file = data_file.with_name(f"{data_file.stem}_schema.json")
        schema_file.write_text(
            encoding="utf-8", data=f"{self.schema_json(indent=YAML_INDENT)}\n"
        )


class SynchronizedPathsYamlModel(YamlModel):
    """Model of a YAML file that synchronizes paths back to the file.

    For example, synchronize complex path structures back to `params.yaml` DVC files for
    pipeline orchestration.
    """

    def __init__(self, data_file: Path, **kwargs):
        """Initialize and update the schema."""
        super().__init__(data_file, **kwargs)

    def get_params(self, data_file: Path) -> dict[str, Paths[Path]]:
        """Get parameters from file, synchronizing paths in the file."""
        params = super().get_params(data_file)
        paths = self.get_paths()
        yaml.dump(params | paths, data_file)
        for i, param in paths.items():
            for j, p in param.items():
                paths[i][j] = apply_to_path_or_paths(p, lambda p_: Path(p_).resolve())
        return params | paths

    def get_paths(self) -> dict[str, Paths[str]]:
        """Get all paths specified in paths-type models."""
        maybe_excludes = self.__exclude_fields__
        excludes = set(maybe_excludes.keys()) if maybe_excludes else set()
        defaults: dict[str, Paths[str]] = {}
        for key, field in self.__fields__.items():
            if key in excludes:
                continue
            if generic_ := get_origin(field.type_):
                type_ = type(generic_)
            else:
                type_ = field.type_
            if issubclass(type_, DefaultPathsModel):
                defaults[key] = type_.get_paths()
        return defaults


def check_pathlike(model: BaseModel, field: str, type_: type):
    """Check that the field is path-like."""
    if not issubclass(type_, Path):
        raise TypeError(
            f"Field <{field}> is not Path-like in {model}, derived from {DefaultPathsModel}."
        )


class DefaultPathsModel(BaseModel):
    """All fields must be path-like and have defaults specified in this model."""

    class Config:
        """Model config."""

        @staticmethod
        def schema_extra(schema: dict[str, Any], model):
            """Replace backslashes with forward slashes in paths."""
            if schema.get("required"):
                raise TypeError(
                    f"Defaults must be specified in {model}, derived from {DefaultPathsModel}."
                )
            for (field, prop), type_ in zip(
                schema["properties"].items(),
                (field.type_ for field in model.__fields__.values()),
                strict=True,
            ):
                # If default is a container, `type_` will be the type of its elements.
                check_pathlike(model, field, type_)
                prop["default"] = apply_to_path_or_paths(prop.get("default"), pathfold)

    @classmethod
    def get_paths(cls) -> Paths[str]:
        """Get the paths for this model."""
        return {
            key: value["default"] for key, value in cls.schema()["properties"].items()
        }


def apply_to_path_or_paths(
    path_or_paths: PathOrPaths[Any], fun: Callable[[Any], Any]
) -> PathOrPaths[Any]:
    """Apply a function to a path, sequence of paths, or mapping of names to paths."""
    if isinstance(path_or_paths, str):
        return fun(path_or_paths)
    elif isinstance(path_or_paths, Sequence):
        return [fun(path) for path in path_or_paths]
    elif isinstance(path_or_paths, Mapping):
        return {key: fun(path) for key, path in path_or_paths.items()}
    else:
        raise TypeError("Type not supported.")


class CreatePathsModel(DefaultPathsModel):
    """Parent directories will be created for all fields in this model."""

    @validator("*", always=True, pre=True, each_item=True)
    @classmethod
    def create_directories(cls, value):
        """Create directories associated with each value."""
        path = Path(value)
        if path.is_file():
            return value
        directory = path.parent if path.suffix else path
        directory.mkdir(parents=True, exist_ok=True)
        return value


def pathfold(path: str) -> str:
    """Return the shortest possible path with forward slashes."""
    return str(prefer_relative_path(Path(path))).replace("\\", "/")


def prefer_relative_path(path: Path) -> Path:
    """Return the path relative to the current working directory if possible."""
    cwd = Path.cwd()
    return path.relative_to(cwd) if path.is_relative_to(cwd) else path
