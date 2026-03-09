from functools import lru_cache
from typing import Annotated, Union

from fastapi import APIRouter, Depends, Response, status
from haystack.dataclasses import ChatMessage

from src.generator_factory import get_chat_generator, get_chat_pipeline
from src.llm_config import ChatGeneratorSettings
from src.llm_evaluator import LlmEvaluator
from src.models import InputResource, PolicyResult, SysError, ValidationError
from src.template import tmp_basic
from src.utility.logger import get_logger


@lru_cache
def get_llm_evaluator() -> LlmEvaluator:
    chat_generator_settings = ChatGeneratorSettings()
    chat_generator = get_chat_generator(chat_generator_settings)
    template = [ChatMessage.from_user(message) for message in tmp_basic.messages]
    #template = [ChatMessage.from_system(message) for message in tmp_basic.messages]
    pipeline = get_chat_pipeline(chat_generator, template)
    return LlmEvaluator(pipeline)
router = APIRouter()

logger = get_logger()


@router.post(
    '/v1/evaluate',
    responses={
        '200': {'model': PolicyResult},
        '400': {'model': ValidationError},
        '500': {'model': SysError},
    },
    tags=['LlmEngine']
)
def evaluate(
    body: InputResource,
    llm_evaluator: Annotated[LlmEvaluator, Depends(get_llm_evaluator)],
    response: Response
) -> Union[PolicyResult, SysError, ValidationError]:
    """
    Return a result based on an input resource
    """

    logger.info(body.model_dump_json(indent=2))

    evaluation = llm_evaluator.evaluate(body.content, body.policy)

    logger.info(evaluation)

    if isinstance(evaluation, SysError):
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    return evaluation