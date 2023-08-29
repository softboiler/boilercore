"""Basic models for this project."""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, get_origin

from pydantic import BaseModel, validator
from ruamel.yaml import YAML

YAML_INDENT = 2
yaml = YAML()
yaml.indent(mapping=YAML_INDENT, sequence=YAML_INDENT, offset=YAML_INDENT)
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
        return (
            yaml.load(data_file)
            if data_file.exists() and data_file.read_text(encoding="utf-8")
            else {}
        )

    def update_schema(self, data_file: Path):
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
        """Initialize, update the schema, and synchronize paths in the file."""
        super().__init__(data_file, **kwargs)

    def get_params(self, data_file: Path) -> dict[str, Any]:
        """Get parameters from file, synchronizing paths in the file."""
        params = super().get_params(data_file)
        params |= self.get_paths()
        yaml.dump(params, data_file)
        return params

    def get_paths(self) -> dict[str, dict[str, str]]:
        """Get all paths specified in paths-type models."""
        maybe_excludes = self.__exclude_fields__
        excludes = set(maybe_excludes.keys()) if maybe_excludes else set()
        defaults: dict[str, dict[str, str]] = {}
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
                default = prop.get("default")
                # If default is a container, `type_` will be the type of its elements.
                check_pathlike(model, field, type_)
                if isinstance(default, str):
                    default = pathfold(default)
                elif isinstance(default, Sequence):
                    default = [pathfold(path) for path in default]
                elif isinstance(default, Mapping):
                    default = {key: pathfold(path) for key, path in default.items()}
                else:
                    raise TypeError("Type not supported.")
                prop["default"] = default

    @classmethod
    def get_paths(cls) -> dict[str, Any]:
        """Get the paths for this model."""
        return {
            key: value["default"] for key, value in cls.schema()["properties"].items()
        }


class CreatePathsModel(DefaultPathsModel):
    """Parent directories will be created for all fields in this model."""

    @validator("*", always=True, pre=True, each_item=True)
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
