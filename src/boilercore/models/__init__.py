"""Basic models."""

from collections.abc import Callable, Iterator, Mapping, Sequence
from itertools import chain
from json import dumps
from pathlib import Path
from types import EllipsisType, GenericAlias
from typing import Annotated, Any, ClassVar, get_args, get_origin

from pydantic import BaseModel, ConfigDict, field_validator
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
            encoding="utf-8",
            data=f"{dumps(self.model_json_schema(), indent=YAML_INDENT)}\n",
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
        excludes = {k for k, v in self.model_fields.items() if v.exclude}
        defaults: dict[str, Paths[str]] = {}
        for key, field in self.model_fields.items():
            if key in excludes:
                continue
            if generic_ := get_origin(field.annotation):
                annotation = type(generic_)
            else:
                annotation = field.annotation
            if issubclass(annotation, DefaultPathsModel):  # pyright: ignore[reportArgumentType]
                defaults[key] = annotation.get_paths()
        return defaults


def check_pathlike(model: BaseModel, field: str, annotation: type | GenericAlias):
    """Check that the field is path-like."""
    for typ in get_types(annotation):
        if isinstance(typ, EllipsisType):
            continue
        if not issubclass(typ, Path):
            raise TypeError(
                f"Field <{field}> is not Path-like in {model}, derived from {DefaultPathsModel}."
            )


def get_types(
    annotation: type | EllipsisType | GenericAlias,
) -> Iterator[type | EllipsisType]:
    """Get types."""
    if isinstance(annotation, type | EllipsisType):
        yield annotation
    elif (origin := get_origin(annotation)) and (args := get_args(annotation)):
        if issubclass(origin, Mapping):
            value_annotation = args[-1]
            yield from get_types(value_annotation)
        elif issubclass(origin, Sequence):
            yield from chain.from_iterable(get_types(a) for a in args)
        elif issubclass(origin, Annotated):
            annotated_type = args[0]
            yield from get_types(annotated_type)
    else:
        raise TypeError("Type not supported.")


def schema_extra(schema: dict[str, Any], model):
    """Replace backslashes with forward slashes in paths."""
    if schema.get("required"):
        raise TypeError(
            f"Defaults must be specified in {model}, derived from {DefaultPathsModel}."
        )
    for (field, prop), annotation in zip(
        schema["properties"].items(),
        (field.annotation for field in model.model_fields.values()),
        strict=True,
    ):
        # If default is a container, `annotation` will be the type of its elements.
        check_pathlike(model, field, annotation)
        prop["default"] = apply_to_path_or_paths(prop.get("default"), pathfold)


class DefaultPathsModel(BaseModel):
    """All fields must be path-like and have defaults specified in this model."""

    model_config: ClassVar[ConfigDict] = ConfigDict(json_schema_extra=schema_extra)

    @classmethod
    def get_paths(cls) -> Paths[str]:
        """Get the paths for this model."""
        return {
            key: value["default"]
            for key, value in cls.model_json_schema()["properties"].items()
        }


def apply_to_path_or_paths(
    path_or_paths: PathOrPaths[Any], fun: Callable[[Any], Any]
) -> PathOrPaths[Any]:
    """Apply a function to a path, sequence of paths, or mapping of names to paths."""
    if isinstance(path_or_paths, Path | str):
        return fun(path_or_paths)
    elif isinstance(path_or_paths, Sequence):
        return [fun(path) for path in path_or_paths]
    elif isinstance(path_or_paths, Mapping):
        return {key: fun(path) for key, path in path_or_paths.items()}
    else:
        raise TypeError("Type not supported.")


def create_directories(path: Path | str) -> None:
    """Create directories."""
    path = Path(path)
    if path.is_file():
        return
    path.mkdir(parents=True, exist_ok=True)


class CreatePathsModel(DefaultPathsModel):
    """Parent directories will be created for all fields in this model."""

    @field_validator("*", mode="before")
    @classmethod
    def create_directories(cls, value):
        """Create directories associated with each value."""
        apply_to_path_or_paths(value, create_directories)
        return value


def pathfold(path: str) -> str:
    """Return the shortest possible path with forward slashes."""
    return str(prefer_relative_path(Path(path))).replace("\\", "/")


def prefer_relative_path(path: Path) -> Path:
    """Return the path relative to the current working directory if possible."""
    cwd = Path.cwd()
    return path.relative_to(cwd) if path.is_relative_to(cwd) else path
