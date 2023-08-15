"""Parameter models for this project."""

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

    def __init__(self, data_file: Path):
        """Initialize and update the schema."""
        params = self.get_params(data_file)
        self.update_schema(data_file)
        super().__init__(**params)

    def get_params(self, data_file: Path) -> dict[str, Any]:
        """Get parameters from file."""
        yaml = YAML()
        yaml.indent(YAML_INDENT)
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

    def __init__(self, data_file: Path):
        """Initialize, update the schema, and synchronize paths in the file."""
        super().__init__(data_file)

    def get_params(self, data_file: Path) -> dict[str, Any]:
        """Get parameters from file, synchronizing paths in the file."""
        yaml = YAML()
        yaml.indent(YAML_INDENT)
        params = (
            yaml.load(data_file)
            if data_file.exists() and data_file.read_text(encoding="utf-8")
            else {}
        )
        params |= self.get_paths()
        yaml.dump(params, data_file)
        return params

    def get_paths(self) -> dict[str, dict[str, str]]:
        """Get all paths specified in paths-type models."""
        maybe_excludes = self.__exclude_fields__
        excludes = set(maybe_excludes.keys()) if maybe_excludes else set()
        defaults: dict[str, dict[str, str]] = {}
        for key, field in self.__fields__.items():
            if generic_ := get_origin(field.type_):
                type_ = type(generic_)
            else:
                type_ = field.type_
            if key not in excludes and issubclass(type_, DefaultPathsModel):
                defaults[key] = type_.get_paths()
        return defaults


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
                if not issubclass(type_, Path):
                    raise TypeError(
                        f"Field <{field}> is not Path-like in {model}, derived from {DefaultPathsModel}."
                    )
                default = prop.get("default")
                if isinstance(default, list | tuple):
                    default = [item.replace("\\", "/") for item in default]
                elif isinstance(default, dict):
                    default = {
                        key: value.replace("\\", "/") for key, value in default.items()
                    }
                else:
                    default = default.replace("\\", "/")
                prop["default"] = default

    @validator("*", always=True, pre=True, each_item=True)
    def check_pathlike(cls, value, field):
        """Check that the value is path-like."""
        if not issubclass(field.type_, Path):
            raise TypeError(
                f"Field is not Path-like in {cls}, derived from {DefaultPathsModel}."
            )
        return value

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
