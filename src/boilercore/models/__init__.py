"""Basic models."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping, Sequence
from functools import partial
from itertools import chain
from json import dumps
from pathlib import Path
from types import EllipsisType, GenericAlias
from typing import Annotated, Any, ClassVar, NamedTuple, get_args, get_origin

from pydantic import BaseModel, ConfigDict, model_validator
from pydantic.fields import FieldInfo
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaWarningKind
from pydantic.types import PathType
from ruamel.yaml import YAML

from boilercore.models.types import PathOrPaths, Paths

YAML_INDENT = 2
yaml = YAML()
yaml.indent(mapping=YAML_INDENT, sequence=YAML_INDENT, offset=YAML_INDENT)
yaml.width = 1000  # Otherwise Ruamel breaks lines illegally
yaml.preserve_quotes = True


class GenerateJsonSchemaNoWarnDefault(GenerateJsonSchema):
    """Don't warn about non-serializable defaults since we handle them."""

    ignored_warning_kinds: ClassVar[set[JsonSchemaWarningKind]] = {  # pyright: ignore[reportIncompatibleVariableOverride]
        "non-serializable-default"
    }


class YamlModel(BaseModel):
    """Model of a YAML file with automatic schema generation.

    Updates a JSON schema next to the YAML file with each initialization.
    """

    def __init__(self, data_file: Path, /, **kwargs):
        """Initialize and update the schema."""
        self.update_schema(data_file)
        super().__init__(**(self.get_params(data_file) | kwargs))

    def get_params(self, data_file: Path) -> dict[str, Any]:
        """Get parameters from file."""
        return yaml.load(data_file) or {} if data_file.exists() else {}

    def update_schema(self, data_file: Path):
        """Update the schema file next to the data file."""
        schema_file = data_file.with_name(f"{data_file.stem}_schema.json")
        schema_file.write_text(
            encoding="utf-8",
            data=f"{dumps(self.model_json_schema(schema_generator=GenerateJsonSchemaNoWarnDefault), indent=YAML_INDENT)}\n",
        )


class SynchronizedPathsYamlModel(YamlModel):
    """Model of a YAML file that synchronizes paths back to the file.

    For example, synchronize complex path structures back to `params.yaml` DVC files for
    pipeline orchestration.
    """

    def __init__(self, data_file: Path, /, **kwargs):
        """Initialize and update the schema."""
        super().__init__(data_file, **kwargs)
        params = self.get_params(data_file)
        for outer_field, value in self.model_fields.items():
            if issubclass((typ := get_field_type(value)), DefaultPathsModel):
                paths = getattr(self, outer_field)
                for field in typ.model_fields:
                    if field == "root":
                        continue
                    params[outer_field][field] = apply_to_path_or_paths(
                        getattr(paths, field), partial(try_relative, other=paths.root)
                    )
        yaml.dump(params, data_file)

    def get_params(self, data_file: Path) -> dict[str, Paths[Path]]:
        """Get parameters from file, synchronizing paths in the file."""
        return super().get_params(data_file) | self.get_paths()

    def get_paths(self) -> dict[str, Paths[str]]:
        """Get all paths specified in paths-type models."""
        defaults: dict[str, Paths[str]] = {}
        for field, value in self.model_fields.items():
            if value.exclude:
                continue
            if issubclass((typ := get_field_type(value)), DefaultPathsModel):
                defaults[field] = typ.get_paths()
        return defaults


def try_relative(path: Path, other: Path) -> str:
    """Try to get a string path relative to another."""
    return (path.relative_to(other) if path.is_relative_to(other) else path).as_posix()


def get_field_type(field: FieldInfo) -> type:
    """Get the type of a field."""
    return (  # pyright: ignore[reportReturnType]
        type(generic_)
        if (generic_ := get_origin(field.annotation))
        else field.annotation
    )


def json_schema_extra(schema: dict[str, Any], model: type[BaseModel]):
    """Replace backslashes with forward slashes in paths."""
    if (reqd := schema.get("required")) and "root" in reqd:
        schema["required"] = []
    if schema["required"]:
        raise TypeError(
            f"Defaults must be specified in {model}, derived from {DefaultPathsModel}."
        )
    for (field, prop), (annotation, default) in zip(
        schema["properties"].items(),
        ((field.annotation, field.default) for field in model.model_fields.values()),
        strict=True,
    ):
        if field == "root":
            continue
        check_pathlike(model, field, annotation)  # pyright: ignore[reportArgumentType]
        prop["default"] = apply_to_path_or_paths(default, lambda path: path.as_posix())


class DefaultPathsModel(BaseModel):
    """All fields must be path-like and have defaults specified in this model."""

    root: Path
    model_config: ClassVar[ConfigDict] = ConfigDict(
        validate_default=True, json_schema_extra=json_schema_extra
    )

    @classmethod
    def get_paths(cls) -> Paths[str]:
        """Get the paths for this model."""
        return {
            key: value["default"]
            for key, value in cls.model_json_schema(
                schema_generator=GenerateJsonSchemaNoWarnDefault
            )["properties"].items()
            if key != "root"
        }


class CreatePathsModel(DefaultPathsModel):
    """Parent directories will be created for all fields in this model."""

    @model_validator(mode="before")
    @classmethod
    def create_directories(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Create directories for directory paths."""
        for field, value in cls.model_fields.items():
            if field == "root":
                continue
            metadata = value.metadata or list(
                chain.from_iterable(
                    v.metadata
                    for v in get_types(value.annotation)  # pyright: ignore[reportArgumentType]
                )
            )
            apply_to_path_or_paths(
                value.default,
                partial(create_directories, metadata=metadata),  # pyright: ignore[reportArgumentType]
            )
        return data


def create_directories(path, metadata: list[Any]):
    """Create directories for directory paths."""
    if PathType("dir") in metadata:
        path.mkdir(parents=True, exist_ok=True)


def check_pathlike(model: type[BaseModel], field: str, annotation: type | GenericAlias):
    """Check that the field is path-like."""
    for typ in get_types(annotation):
        if isinstance(typ.typ, EllipsisType):
            continue
        if not issubclass(typ.typ, Path):
            raise TypeError(
                f"Field <{field}> is not Path-like in {model}, derived from {DefaultPathsModel}."
            )


class Typ(NamedTuple):
    """A type and its metadata."""

    typ: type | EllipsisType
    metadata: list[Any]


def get_types(
    annotation: type | EllipsisType | GenericAlias, metadata: list[Any] | None = None
) -> Iterator[Typ]:
    """Get types for scalar, mapping, sequence, and annotated types."""
    if isinstance(annotation, type | EllipsisType):
        yield Typ(annotation, metadata or [])
    elif (origin := get_origin(annotation)) and (args := get_args(annotation)):
        if issubclass(origin, Mapping):
            value_annotation = args[-1]
            yield from get_types(value_annotation)
        elif issubclass(origin, Sequence):
            yield from chain.from_iterable(get_types(a) for a in args)
        elif issubclass(origin, Annotated):
            typ, *metadata = args
            yield from get_types(typ, metadata)
    else:
        raise TypeError("Type not supported.")


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
