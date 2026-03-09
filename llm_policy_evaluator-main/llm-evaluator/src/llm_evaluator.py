import json
import os
from typing import Union

import httpx
import yaml
from fastapi.encoders import jsonable_encoder
from haystack import Pipeline
from haystack.dataclasses import ChatMessage

from src.models import PolicyResult, SysError
from src.utility import json_utils
from src.utility.logger import get_logger
from src.utility.unit_converter import byte2kilobyte

logger = get_logger()


class LlmEvaluator:
    def __init__(self, pipeline: Pipeline) -> None:
        self.pipeline = pipeline

        env_var_name: str = 'MAX_DESCRIPTOR_SIZE_IN_KB'
        default_max_kilobyte: int = 1024 * 10 # 10 MB
        max_kilobyte: str = os.getenv(env_var_name, str(default_max_kilobyte))

        try:
            self.max_kilobyte: int = int(max_kilobyte)
        except ValueError:
            raise ValueError(f'Environment variable "{env_var_name}" must be an integer')

    def evaluate(self, content: str, policy: str) -> Union[PolicyResult, SysError]:
        """
            This method is responsible for evaluating the given content using the given policy.

            Params:
                - content (str): the content to be evaluated.
                - policy (str): the policy used for evaluating the content.

            Returns:
                Union[PolicyResult, SysError]: when the evaluation is properly executed, the method returns a
                PolicyResult containing the evaluation result, otherwise it returns a SysError when an error occurs.
        """
        try:
            if byte2kilobyte(len(content.encode("utf-8"))) > self.max_kilobyte:
                return PolicyResult(
                    satisfiesPolicy=False,
                    details={},
                    errors=['Descriptor is too large to be evaluated.']
                )

            yaml_content = yaml.safe_load(content)
            safe_json = jsonable_encoder(yaml_content)
            json_content = json.dumps(safe_json, separators=(",", ":"), ensure_ascii=False)

            policy = policy.strip()

            response = self.pipeline.run({'prompt_builder': {'content': json_content, 'policy': policy}})
            reply: Union[str, ChatMessage] = response['llm']['replies'][0]
            reply = reply if isinstance(reply, str) else reply.text
            reply = json_utils.sanitize(reply)
            logger.debug('Response from LLM: %s', reply)
            json_reply = json.loads(reply)
            return PolicyResult(
                satisfiesPolicy=json_reply['satisfiesPolicy'],
                details=json_reply['details'],
                errors=json_reply['errors']
            )
        except json.decoder.JSONDecodeError:
            logger.exception('Error parsing response from LLM as JSON')
            return SysError(error='Unable to decode LLM response. Please try again later.')
        except httpx.ConnectError:
            logger.exception("Network error")
            return SysError(error="Network error: Unable to reach the LLM API server due to a connection issue. "
                                  "Please try again later. If the issue persists, contact the platform support team.")
        except Exception as e:
            logger.exception('Unexpected error')
            detail = getattr(e, 'message', str(e))
            return SysError(
                error=(
                    f'An unexpected error occurred. '
                    f'Please try again and if the error persists, contact the platform team. Details: {str(detail)}')
            )