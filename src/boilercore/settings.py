"""Settings."""

from pydantic import BaseModel, ConfigDict
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

import boilercore
import boilercore.settings_models
from boilercore import settings_models
from boilercore.paths import get_module_name
from boilercore.settings_models import (
    customise_sources,
    get_settings_paths,
    set_plugin_settings,
    sync_settings_schema,
)


class Constants(BaseModel):
    """Constants."""

    package_name: str = get_module_name(boilercore)


const = Constants()


paths = get_settings_paths(boilercore)


class PluginModelConfig(BaseSettings):
    """Pydantic plugin model configuration."""

    source_relative: bool = True

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        *_args: PydanticBaseSettingsSource,
        **_kwds: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Source settings from init and TOML."""
        return customise_sources(settings_cls, init_settings, paths.plugin_settings)


class Settings(BaseSettings):
    """Package settings."""

    model_config = SettingsConfigDict(use_attribute_docstrings=True)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        *_args: PydanticBaseSettingsSource,
        **_kwds: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Source settings from init and TOML."""
        return customise_sources(settings_cls, init_settings, paths.settings)


for path, model in zip(
    paths.all_dev_settings if paths.in_dev else paths.all_cwd_settings,
    (PluginModelConfig, Settings),
    strict=True,
):
    sync_settings_schema(path, model)

default = Settings()
default_plugin_config = PluginModelConfig()
default_plugin_config_dict = set_plugin_settings(
    const.package_name, default_plugin_config
)


def get_plugin_settings(model_config: ConfigDict | SettingsConfigDict):
    """Get Pydantic plugin model configuration.

    ```Python
    boilercore_pydantic_plugin_settings = get_plugin_settings(Model.model_config)
    ```
    """
    return settings_models.get_plugin_settings(
        model_config=model_config,
        package_name=const.package_name,
        config=PluginModelConfig,
    )
