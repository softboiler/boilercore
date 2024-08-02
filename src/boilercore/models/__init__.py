"""Basic models."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping, Sequence
from functools import partial
from itertools import chain
from json import dumps
from pathlib import Path
from types import EllipsisType, GenericAlias
from typing import Annotated, Any, ClassVar, NamedTuple, get_args, get_origin

from pydantic import BaseModel, ConfigDict, FilePath, model_validator
from pydantic.fields import FieldInfo
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaWarningKind
from pydantic.types import PathType
from pydantic_settings import (
    BaseSettings,
    InitSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
    sources,
)
from pydantic_settings.sources import DEFAULT_PATH
from ruamel.yaml import YAML

from boilercore.models.types import PathOrPaths, Paths

SOURCE = "source"
"""Name of the settings source model attribute."""
ROOT = "root"
"""Name of the root path model attribute."""
YAML_INDENT = 2
"""YAML indentation."""
yaml = YAML()
yaml.indent(mapping=YAML_INDENT, sequence=YAML_INDENT, offset=YAML_INDENT)
yaml.width = 1000  # Otherwise Ruamel breaks lines illegally
yaml.preserve_quotes = True


class GenerateJsonSchemaNoWarnDefault(GenerateJsonSchema):
    """Don't warn about non-serializable defaults since we handle them."""

    ignored_warning_kinds: ClassVar[set[JsonSchemaWarningKind]] = {  # pyright: ignore[reportIncompatibleVariableOverride]
        "non-serializable-default"
    }


def yaml_json_schema_extra(schema: dict[str, Any]):
    """Don't require `source`."""
    if req := schema.get("required"):
        schema["required"] = [r for r in req if r != SOURCE]


class SynchronizedPathsYamlModel(BaseSettings):
    """Model of a YAML file that synchronizes paths back to the file.

    For example, synchronize complex path structures back to `params.yaml` DVC files for
    pipeline orchestration.
    """

    source: FilePath
    model_config = SettingsConfigDict(
        yaml_file_encoding="utf-8", json_schema_extra=yaml_json_schema_extra
    )

    def __init__(self, **kwargs):
        """Initialize and update the schema."""
        super().__init__(**kwargs)
        self.update_schema(self.source)

    def update_schema(self, data_file: Path):
        """Update the schema file next to the data file."""
        schema_file = data_file.with_name(f"{data_file.stem}_schema.json")
        schema_file.write_text(
            encoding="utf-8",
            data=f"{dumps(self.model_json_schema(schema_generator=GenerateJsonSchemaNoWarnDefault), indent=YAML_INDENT)}\n",
        )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        *_args: PydanticBaseSettingsSource,
        **_kwds: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Customize settings sources."""
        default_paths_settings = DefaultPathsSettingsSource(
            settings_cls,
            init_settings.init_kwargs,  # pyright: ignore[reportAttributeAccessIssue]
        )
        return (
            init_settings,
            default_paths_settings,
            NonPathsYamlConfigSettingsSource(
                settings_cls,
                yaml_file=get_yaml_file(settings_cls, init_settings.init_kwargs),  # pyright: ignore[reportArgumentType, reportAttributeAccessIssue]
                default_paths_kwargs=default_paths_settings.init_kwargs,
            ),
        )


class DefaultPathsSettingsSource(InitSettingsSource):
    """Source class that loads defaults."""

    def __init__(self, settings_cls: type[BaseSettings], init_kwargs: dict[str, Any]):
        super().__init__(settings_cls, get_default_paths(settings_cls, init_kwargs))


class NonPathsYamlConfigSettingsSource(YamlConfigSettingsSource):
    """Source class that loads non-paths from `yaml`."""

    def __init__(
        self,
        settings_cls: type[BaseSettings],
        default_paths_kwargs: dict[str, Any],
        yaml_file: sources.PathType | None = DEFAULT_PATH,
        yaml_file_encoding: str | None = None,
    ):
        super().__init__(
            settings_cls=settings_cls,
            yaml_file=yaml_file,
            yaml_file_encoding=yaml_file_encoding,
        )
        source = yaml.load(yaml_file) or {} if Path(yaml_file).exists() else {}  # pyright: ignore[reportArgumentType]
        kwargs: dict[str, Any] = {}
        for field, value in settings_cls.model_fields.items():
            if field == "source":
                continue
            if issubclass(get_field_type(value), DefaultPathsModel):
                source[field] = {
                    key: apply_to_path_or_paths(
                        v,
                        partial(
                            lambda path: (
                                path.relative_to(Path.cwd())
                                if path.is_relative_to(Path.cwd())
                                else path
                            ).as_posix()
                        ),
                    )
                    for key, v in default_paths_kwargs[field].items()
                    if key != ROOT
                }
            elif kwarg := self.init_kwargs.get(field):
                kwargs[field] = kwarg
        yaml.dump(source, Path(yaml_file))  # pyright: ignore[reportArgumentType]
        self.init_kwargs = kwargs


def default_paths_json_schema_extra(schema: dict[str, Any], model: type[BaseModel]):
    """Replace backslashes with forward slashes in paths."""
    if schema.get("required"):
        raise TypeError(
            f"Defaults must be specified in {model}, derived from {DefaultPathsModel}."
        )
    for (field, prop), (annotation, default) in zip(
        schema["properties"].items(),
        ((field.annotation, field.default) for field in model.model_fields.values()),
        strict=True,
    ):
        if field == ROOT:
            continue
        check_pathlike(model, field, annotation)  # pyright: ignore[reportArgumentType]
        prop["default"] = apply_to_path_or_paths(default, lambda path: path.as_posix())


class DefaultPathsModel(BaseModel):
    """All fields must be path-like and have defaults specified in this model."""

    root: Path
    model_config: ClassVar[ConfigDict] = ConfigDict(
        validate_default=True, json_schema_extra=default_paths_json_schema_extra
    )

    @classmethod
    def get_default_paths(cls, root: Path) -> Paths[str]:
        """Get default paths for this model."""
        return {
            key: apply_to_path_or_paths(value["default"], lambda path: root / path)
            for key, value in cls.model_json_schema(
                schema_generator=GenerateJsonSchemaNoWarnDefault
            )["properties"].items()
            if key != ROOT
        }


class CreatePathsModel(DefaultPathsModel):
    """Parent directories will be created for all fields in this model."""

    @model_validator(mode="before")
    @classmethod
    def create_directories(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Create directories for directory paths."""
        root = data.get("root", cls.model_fields[ROOT].default)
        for field, value in cls.model_fields.items():
            if field == ROOT:
                continue
            metadata = value.metadata or list(
                chain.from_iterable(
                    v.metadata
                    for v in get_types(value.annotation)  # pyright: ignore[reportArgumentType]
                )
            )
            data[field] = apply_to_path_or_paths(
                value.default,
                partial(make_absolute_and_create, other=root, metadata=metadata),
            )
        return data


def get_yaml_file(
    settings_cls: type[BaseSettings], init_kwargs: dict[str, Any]
) -> Path:
    """Get YAML file for settings."""
    if init := init_kwargs.get(SOURCE):
        if not Path(init).exists():
            Path(init).touch()
        return init
    elif model := settings_cls.model_fields[SOURCE].default:
        if not Path(model).exists():
            Path(model).touch()
        return model
    raise ValueError("No source file specified.")


def get_field_type(field: FieldInfo) -> type:
    """Get the type of a field."""
    return (  # pyright: ignore[reportReturnType]
        type(generic_)
        if (generic_ := get_origin(field.annotation))
        else field.annotation
    )


def get_root(typ: type[DefaultPathsModel], field: str, init_kwargs: dict[str, Any]):
    """Get the root path of a model."""
    return (
        root
        if (init := init_kwargs.get(field)) and (root := init.get(ROOT))
        else typ.model_fields[ROOT].default
    )


def get_default_paths(
    model: type[BaseModel] | BaseModel, init_kwargs: dict[str, Any]
) -> dict[str, Paths[str]]:
    """Get default paths of a model."""
    defaults: dict[str, Paths[str]] = {}
    for field, value in model.model_fields.items():
        if issubclass((typ := get_field_type(value)), DefaultPathsModel):
            defaults[field] = typ.get_default_paths(get_root(typ, field, init_kwargs))
    return defaults


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


def check_pathlike(model: type[BaseModel], field: str, annotation: type | GenericAlias):
    """Check that the field is path-like."""
    for typ in get_types(annotation):
        if isinstance(typ.typ, EllipsisType):
            continue
        if not issubclass(typ.typ, Path):
            raise TypeError(
                f"Field <{field}> is not Path-like in {model}, derived from {DefaultPathsModel}."
            )


def make_absolute_and_create(path, other: Path, metadata: list[Any]):
    """Create directories for directory paths."""
    absolute = other / path
    if PathType("dir") in metadata:
        absolute.mkdir(parents=True, exist_ok=True)
    return absolute


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
