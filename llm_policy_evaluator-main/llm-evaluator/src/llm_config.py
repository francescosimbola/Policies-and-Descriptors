from typing import Any, Dict, Optional, Tuple, Type

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, YamlConfigSettingsSource


class ChatGeneratorSettings(BaseSettings):
    class_name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return init_settings, YamlConfigSettingsSource(settings_cls, 'config/generator.yaml')