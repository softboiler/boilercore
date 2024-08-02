"""Basic models."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping, Sequence
from functools import partial
from itertools import chain
from json import dumps
from pathlib import Path
from types import EllipsisType, GenericAlias
from typing import Annotated, Any, ClassVar, NamedTuple, get_args, get_origin

from pydantic import BaseModel, ConfigDict, DirectoryPath, FilePath, model_validator
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
INDENT = 2
"""Indentation for YAML and JSON."""
ENCODING = "utf-8"
"""File encoding."""
yaml = YAML()
"""Customized YAML loader/dumper."""
yaml.indent(mapping=INDENT, sequence=INDENT, offset=INDENT)
yaml.width = 1000  # Otherwise Ruamel breaks lines illegally
yaml.preserve_quotes = True


class BoilercorePydanticPluginSettings(BaseModel):
    """Plugin settings for boilercore."""

    source_relative: bool = True


def validate_settings(
    model_config: SettingsConfigDict,
) -> BoilercorePydanticPluginSettings:
    """Validate settings."""
    return BoilercorePydanticPluginSettings(
        **(
            settings
            if (plugin := model_config.get("plugin_settings"))  # pyright: ignore[reportCallIssue]
            and (settings := plugin.get("boilercore"))
            else {}
        )
    )


def yaml_json_schema_extra(schema: dict[str, Any]):
    """Don't require `source`."""
    if req := schema.get("required"):
        schema["required"] = [r for r in req if r != SOURCE]


class SynchronizedPathsYamlModel(BaseSettings):
    """Model of a YAML file that synchronizes paths back to the file.

    For example, synchronize complex path structures back to `params.yaml` DVC files for
    pipeline orchestration.
    """

    model_config = SettingsConfigDict(
        yaml_file_encoding=ENCODING,
        json_schema_extra=yaml_json_schema_extra,
        plugin_settings={"boilercore": {"source_relative": True}},
    )
    source: FilePath

    def __init__(self, **kwargs):
        """Initialize and update  schema."""
        super().__init__(**kwargs)
        source_schema = self.source.with_name(f"{self.source.stem}_schema.json")
        source_schema.write_text(
            encoding=ENCODING,
            data=dumps(
                self.model_json_schema(
                    schema_generator=GenerateJsonSchemaNoWarnDefault
                ),
                indent=INDENT,
            )
            + "\n",
        )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        *_args: PydanticBaseSettingsSource,
        **_kwds: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Customize settings sources.

        Prioritize values passed during initialization, then values from YAML which are
        not part of paths models.
        """
        return (
            init_settings,
            default_paths := DefaultPathsSettingsSource(
                settings_cls,
                init_settings.init_kwargs,  # pyright: ignore[reportAttributeAccessIssue]
            ),
            NonPathsModelYamlConfigSettingsSource(
                settings_cls,
                default_paths.init_kwargs,
                yaml_file=get_yaml_file(settings_cls, init_settings.init_kwargs),  # pyright: ignore[reportArgumentType, reportAttributeAccessIssue]
            ),
        )


def get_yaml_file(model: type[BaseSettings], init_kwargs: dict[str, Any]) -> Path:
    """Get YAML file for settings."""
    if init := init_kwargs.get(SOURCE):
        if not Path(init).exists():
            Path(init).touch()
        return init
    elif default := model.model_fields[SOURCE].default:
        if not Path(default).exists():
            Path(default).touch()
        return default
    raise ValueError("No source file specified.")


class DefaultPathsSettingsSource(InitSettingsSource):
    """Settings source class that gets default paths from the model."""

    def __init__(self, settings_cls: type[BaseSettings], init_paths: dict[str, Any]):
        defaults: dict[str, Paths[str]] = {}
        for field, value in settings_cls.model_fields.items():
            if issubclass((typ := get_field_type(value)), DefaultPathsModel):
                defaults[field] = typ.get_default_paths(
                    get_root(typ, field, init_paths)
                )
        super().__init__(settings_cls, defaults)


class NonPathsModelYamlConfigSettingsSource(YamlConfigSettingsSource):
    """Settings source classs that loads from YAML, excluding paths model values.

    Also synchronizes paths model default values back to the YAML.
    """

    def __init__(
        self,
        settings_cls: type[BaseSettings],
        default_paths: dict[str, Paths[str]],
        yaml_file: sources.PathType | None = DEFAULT_PATH,
        _yaml_file_encoding: str | None = None,
    ):
        super().__init__(
            settings_cls=settings_cls, yaml_file=yaml_file, yaml_file_encoding=ENCODING
        )
        yaml_path = Path(yaml_file)  # pyright: ignore[reportArgumentType]
        source = yaml.load(yaml_path) or {} if yaml_path.exists() else {}
        # ? Start with extra source kwargs in case config allows them
        non_pathsmodel_source_kwargs = _extra_source_kwargs = {
            field: source[field]
            for field in [
                f for f in source if f not in settings_cls.model_fields and f != SOURCE
            ]
        }
        # ? Sync paths model paths back to source and populate kwargs with others
        for field, info in settings_cls.model_fields.items():
            if field == SOURCE:
                continue
            if issubclass(get_field_type(info), DefaultPathsModel):
                source[field] = {
                    paths_model_field: apply_to_paths(
                        value,
                        partial(
                            lambda path, source_relative: (
                                path.relative_to(yaml_path.parent)
                                if source_relative
                                and path.is_relative_to(yaml_path.parent)
                                else path
                            ).as_posix(),
                            source_relative=validate_settings(
                                settings_cls.model_config
                            ).source_relative,
                        ),
                    )
                    for paths_model_field, value in default_paths[field].items()
                    if paths_model_field != ROOT
                }
                continue
            if kwarg := self.init_kwargs.get(field):
                non_pathsmodel_source_kwargs[field] = kwarg
                continue
        yaml.dump(source, yaml_path)
        self.init_kwargs = non_pathsmodel_source_kwargs


def default_paths_json_schema_extra(schema: dict[str, Any], model: type[BaseModel]):
    """Replace backslashes with forward slashes in paths."""
    if schema.get("required"):
        raise ValueError(
            f"Defaults must be specified in {model}, derived from {DefaultPathsModel}."
        )
    for (field, prop), (annotation, default) in zip(
        schema["properties"].items(),
        ((field.annotation, field.default) for field in model.model_fields.values()),
        strict=True,
    ):
        if field == ROOT:
            continue
        for typ in get_types(annotation):  # pyright: ignore[reportArgumentType]
            if isinstance(typ.typ, EllipsisType):
                continue
            if not issubclass(typ.typ, Path):
                raise TypeError(
                    f"Field <{field}> is not Path-like in {model}, derived from {DefaultPathsModel}."
                )
        prop["default"] = apply_to_paths(default, lambda path: path.as_posix())


class DefaultPathsModel(BaseModel):
    """All fields must be path-like and have defaults specified in this model."""

    root: DirectoryPath
    model_config: ClassVar[ConfigDict] = ConfigDict(
        validate_default=True, json_schema_extra=default_paths_json_schema_extra
    )

    @classmethod
    def get_default_paths(cls, root: Path) -> Paths[str]:
        """Get default paths for this model."""
        return {
            field: apply_to_paths(prop["default"], lambda path: root / path)
            for field, prop in cls.model_json_schema(
                schema_generator=GenerateJsonSchemaNoWarnDefault
            )["properties"].items()
            if field != ROOT
        }


class CreatePathsModel(DefaultPathsModel):
    """Parent directories will be created for all fields in this model."""

    @model_validator(mode="before")
    @classmethod
    def create_directories(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Create directories for directory paths."""
        root = get_root(cls, ROOT, data)
        for field, info in cls.model_fields.items():
            if field == ROOT:
                continue
            metadata = info.metadata or list(
                chain.from_iterable(
                    typ.metadata
                    for typ in get_types(info.annotation)  # pyright: ignore[reportArgumentType]
                )
            )
            data[field] = apply_to_paths(
                info.default,
                partial(make_absolute_and_create, root=root, metadata=metadata),
            )
        return data


def make_absolute_and_create(path, root: Path, metadata: list[Any]):
    """Create directories for directory paths."""
    absolute = root / path
    if PathType("dir") in metadata:
        absolute.mkdir(parents=True, exist_ok=True)
    return absolute


class GenerateJsonSchemaNoWarnDefault(GenerateJsonSchema):
    """Don't warn about non-serializable defaults since we handle them."""

    ignored_warning_kinds: ClassVar[set[JsonSchemaWarningKind]] = {  # pyright: ignore[reportIncompatibleVariableOverride]
        "non-serializable-default"
    }


def get_field_type(field: FieldInfo) -> type:
    """Get the type of a field."""
    return (  # pyright: ignore[reportReturnType]
        type(generic_)
        if (generic_ := get_origin(field.annotation))
        else field.annotation
    )


def get_root(model: type[DefaultPathsModel], field: str, init_kwargs: dict[str, Any]):
    """Get the root path of a model."""
    root = (
        root
        if (init := init_kwargs.get(field)) and (root := init.get(ROOT))
        else model.model_fields[ROOT].default
    )
    if not root.is_absolute():
        raise ValueError(
            f"Root path must be absolute in {model}, derived from {DefaultPathsModel}."
        )
    return root


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
            yield from get_types(_value_annotation := args[-1])
        elif issubclass(origin, Sequence):
            yield from chain.from_iterable(get_types(arg) for arg in args)
        elif issubclass(origin, Annotated):
            typ, *metadata = args
            yield from get_types(typ, metadata)
    else:
        raise TypeError(
            "\n".join([
                f"Unsupported type found in {annotation}. Supported types are scalar,"
                "mapping, sequence, and annotated types."
            ])
        )


def apply_to_paths(
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
        raise TypeError(
            "\n".join([
                f"Type of {path_or_paths} not supported. Supported types are a path,"
                "sequence of paths, or mapping of names to paths."
            ])
        )
