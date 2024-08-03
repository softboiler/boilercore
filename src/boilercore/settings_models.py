"""Settings models."""

from collections.abc import Iterable
from json import dumps
from pathlib import Path
from site import getsitepackages
from types import ModuleType

from pydantic import BaseModel
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    YamlConfigSettingsSource,
)

from boilercore.paths import get_module_name, get_package_dir


class Paths(BaseModel):
    """Settings model paths."""

    cwd_plugin_settings: Path
    dev_plugin_settings: Path
    plugin_settings: list[Path]

    cwd_settings: Path
    dev_settings: Path
    settings: list[Path]

    all_cwd_settings: list[Path]
    all_dev_settings: list[Path]

    in_dev: bool


def get_settings_paths(module: ModuleType) -> Paths:
    """Get settings model paths."""
    package_dir = get_package_dir(module)
    package_name = get_module_name(module)
    return Paths(
        cwd_plugin_settings=(
            cwd_plugin_settings := Path.cwd() / f"{package_name}_plugin.yaml"
        ),
        dev_plugin_settings=(
            dev_plugin_settings := package_dir / "settings_plugin.yaml"
        ),
        plugin_settings=[cwd_plugin_settings, dev_plugin_settings],
        cwd_settings=(cwd_settings := Path.cwd() / Path(f"{package_name}.yaml")),
        dev_settings=(dev_settings := package_dir / "settings.yaml"),
        settings=[cwd_settings, dev_settings],
        all_cwd_settings=[cwd_plugin_settings, cwd_settings],
        all_dev_settings=[dev_plugin_settings, dev_settings],
        in_dev=not (
            getsitepackages() and package_dir.is_relative_to(Path(getsitepackages()[0]))
        ),
    )


def get_yaml_sources(
    settings_cls: type[BaseSettings], paths: Iterable[Path], encoding: str = "utf-8"
) -> tuple[YamlConfigSettingsSource, ...]:
    """Source settings from init and TOML."""
    sources: list[YamlConfigSettingsSource] = []
    for yaml_file in paths:
        source = YamlConfigSettingsSource(
            settings_cls, yaml_file, yaml_file_encoding=encoding
        )
        if source.init_kwargs.get("$schema"):
            del source.init_kwargs["$schema"]
        sources.append(source)
    return tuple(sources)


def customise_sources(
    settings_cls: type[BaseSettings],
    init_settings: PydanticBaseSettingsSource,
    yaml_files: Iterable[Path],
    encoding: str = "utf-8",
):
    """Source settings from init and YAML."""
    return (init_settings, *get_yaml_sources(settings_cls, yaml_files, encoding))


def get_plugin_settings(
    package_name: str, config: BaseSettings
) -> dict[str, BaseSettings]:
    """Get Pydantic plugin model configuration.

    ```Python
    model_config = SettingsConfigDict(
        plugin_settings={"boilercv_docs": PluginModelConfig()}
    )
    ```
    """
    return {package_name: config}


def sync_settings_schema(
    path: Path, model: type[BaseModel], encoding: str = "utf-8"
) -> None:
    """Create settings file and update its schema."""
    if not path.exists():
        path.touch()
    schema = path.with_name(f"{path.stem}_schema.json")
    schema.write_text(
        encoding=encoding, data=f"{dumps(model.model_json_schema(), indent=2)}\n"
    )
