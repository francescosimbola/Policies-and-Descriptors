from typing import Any

import httpx
import pytest
from _pytest.monkeypatch import MonkeyPatch
from haystack import Pipeline
from haystack.dataclasses import ChatMessage

from src.llm_evaluator import LlmEvaluator
from src.models import PolicyResult, SysError


def test_llm_evaluator_descriptor_size_over_limit(monkeypatch: MonkeyPatch) -> None:
    def mock_return(_: dict[str, Any]) -> dict[str, Any]:
        json_str = '{"satisfiesPolicy": true, "errors": [], "details": {}}'
        return {'llm': {'replies': [json_str]}}

    pipeline = Pipeline()
    llm_evaluator = LlmEvaluator(pipeline)
    content = 'a' * 1024 * (llm_evaluator.max_kilobyte + 1)
    policy = ''

    monkeypatch.setattr(pipeline, 'run', mock_return)

    actual = llm_evaluator.evaluate(content, policy)
    assert actual is not None
    assert isinstance(actual, PolicyResult)
    assert actual.satisfiesPolicy is False
    assert actual.errors == ['Descriptor is too large to be evaluated.']
    assert actual.details == {}


def test_llm_evaluator_env_var_not_integer(monkeypatch: MonkeyPatch) -> None:
    env_var_name: str = 'MAX_DESCRIPTOR_SIZE_IN_KB'

    monkeypatch.setenv(env_var_name, 'NaN')

    pipeline = Pipeline()

    with pytest.raises(ValueError, match=f'Environment variable "{env_var_name}" must be an integer'):
        LlmEvaluator(pipeline)

def test_llm_evaluator_return_str(monkeypatch: MonkeyPatch) -> None:
    def mock_return(_: dict[str, Any]) -> dict[str, Any]:
        json_str = '{"satisfiesPolicy": false, "errors": [], "details": {}}'
        return {'llm': {'replies': [json_str]}}

    pipeline = Pipeline()
    llm_evaluator = LlmEvaluator(pipeline)
    content = ''
    policy = ''

    monkeypatch.setattr(pipeline, 'run', mock_return)

    actual = llm_evaluator.evaluate(content, policy)

    assert actual is not None
    assert isinstance(actual, PolicyResult)
    assert actual.satisfiesPolicy is False
    assert actual.errors == []
    assert actual.details == {}


def test_llm_evaluator_return_chat_message(monkeypatch: MonkeyPatch) -> None:
    def mock_return(_: dict[str, Any]) -> dict[str, Any]:
        json_str = '{"satisfiesPolicy": false, "errors": [], "details": {}}'
        chat_message = ChatMessage.from_assistant(json_str)
        return {'llm': {'replies': [chat_message]}}

    pipeline = Pipeline()
    llm_evaluator = LlmEvaluator(pipeline)
    content = ''
    policy = ''

    monkeypatch.setattr(pipeline, 'run', mock_return)

    actual = llm_evaluator.evaluate(content, policy)

    assert actual is not None
    assert isinstance(actual, PolicyResult)
    assert actual.satisfiesPolicy is False
    assert actual.errors == []
    assert actual.details == {}


def test_llm_evaluator_json_error(monkeypatch: MonkeyPatch) -> None:
    def mock_return(_: dict[str, Any]) -> dict[str, Any]:
        malformed_json_str = 'malformed_json_str'
        return {'llm': {'replies': [malformed_json_str]}}

    pipeline = Pipeline()
    llm_evaluator = LlmEvaluator(pipeline)
    content = ''
    policy = ''

    monkeypatch.setattr(pipeline, 'run', mock_return)

    actual = llm_evaluator.evaluate(content, policy)

    assert actual is not None
    assert isinstance(actual, SysError)
    assert actual.error == 'Unable to decode LLM response. Please try again later.'


def test_llm_evaluator_exception(monkeypatch: MonkeyPatch) -> None:
    def mock_return(_: dict[str, Any]) -> dict[str, Any]:
        raise Exception()

    pipeline = Pipeline()
    llm_evaluator = LlmEvaluator(pipeline)
    content = ''
    policy = ''

    monkeypatch.setattr(pipeline, 'run', mock_return)

    actual = llm_evaluator.evaluate(content, policy)

    assert actual is not None
    assert isinstance(actual, SysError)
    assert actual.error == (
        'An unexpected error occurred. Please try again and if the error persists, contact the platform team. Details: '
    )

def test_llm_evaluator_exception_endpoint(monkeypatch: MonkeyPatch) -> None:
    def mock_return(_: dict[str, Any]) -> dict[str, Any]:
        raise httpx.ConnectError("Network error")

    pipeline = Pipeline()
    llm_evaluator = LlmEvaluator(pipeline)
    content = ''
    policy = ''

    monkeypatch.setattr(pipeline, 'run', mock_return)

    actual = llm_evaluator.evaluate(content, policy)

    assert actual is not None
    assert isinstance(actual, SysError)
    assert actual.error == (
        'Network error: Unable to reach the LLM API server due to a connection issue. Please try again later. '
        'If the issue persists, contact the platform support team.'
    )


def test_llm_evaluator_exception_message(monkeypatch: MonkeyPatch) -> None:
    class CustomException(Exception):
        def __init__(self) -> None:
            self.message = "Attribute error message"

    def mock_return(_: dict[str, Any]) -> dict[str, Any]:
        raise CustomException()

    pipeline = Pipeline()
    llm_evaluator = LlmEvaluator(pipeline)
    content = ''
    policy = ''
    monkeypatch.setattr(pipeline, 'run', mock_return)

    actual = llm_evaluator.evaluate(content, policy)

    assert actual is not None
    assert isinstance(actual, SysError)
    assert actual.error == (
        'An unexpected error occurred. '
        'Please try again and if the error persists, contact the platform team. Details: Attribute error message'
    )