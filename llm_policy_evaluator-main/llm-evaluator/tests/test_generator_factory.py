from typing import Any, Dict, List

import pytest
from haystack import Pipeline
from haystack.components.generators.chat import AzureOpenAIChatGenerator
from haystack.dataclasses import ChatMessage
from haystack.utils import Secret

from src.generator_factory import GeneratorNotFound, get_chat_generator, get_chat_pipeline
from src.llm_config import ChatGeneratorSettings


def test_get_chat_generator_ok() -> None:
    config = {'azure_endpoint': 'azure_endpoint', 'api_key': Secret.from_token('api_key')}
    chat_generator_settings = ChatGeneratorSettings(class_name='AzureOpenAIChatGenerator', config=config)

    actual = get_chat_generator(chat_generator_settings)

    assert actual is not None
    assert isinstance(actual, AzureOpenAIChatGenerator)


def test_get_chat_generator_class_name_none() -> None:
    class_name = None
    config = None
    chat_generator_settings = ChatGeneratorSettings(class_name=class_name, config=config)

    with pytest.raises(ValueError, match='The field "class_name" cannot be None'):
        get_chat_generator(chat_generator_settings)


def test_get_chat_generator_config_none() -> None:
    class_name = 'AzureOpenAIChatGenerator'
    config = None
    chat_generator_settings = ChatGeneratorSettings(class_name=class_name, config=config)

    with pytest.raises(ValueError, match='The field "config" cannot be None'):
        get_chat_generator(chat_generator_settings)


def test_get_chat_generator_fail_missing_config() -> None:
    config: Dict[str, Any] = {}
    chat_generator_settings = ChatGeneratorSettings(class_name='AzureOpenAIChatGenerator', config=config)

    with pytest.raises(Exception):
        get_chat_generator(chat_generator_settings)


def test_get_chat_generator_fail_not_existing_generator() -> None:
    class_name = 'NonExistingGenerator'
    config: Dict[str, Any] = {}
    chat_generator_settings = ChatGeneratorSettings(class_name=class_name, config=config)

    with pytest.raises(GeneratorNotFound, match=f'Generator "{class_name}" not found'):
        get_chat_generator(chat_generator_settings)


def test_get_chat_pipeline_ok() -> None:
    config = {'azure_endpoint': 'azure_endpoint', 'api_key': Secret.from_token('api_key')}
    chat_generator_settings = ChatGeneratorSettings(class_name='AzureOpenAIChatGenerator', config=config)
    chat_generator_settings.class_name = 'AzureOpenAIChatGenerator'
    chat_generator_settings.config = config
    chat_generator = get_chat_generator(chat_generator_settings)
    template: List[ChatMessage] = []

    actual = get_chat_pipeline(chat_generator, template)

    assert actual is not None
    assert isinstance(actual, Pipeline)