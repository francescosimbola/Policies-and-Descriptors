from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class InputResource(BaseModel):
    content: str = Field(
        ...,
        description='The content of the resource to be evaluated. The content can be any type of data, such as a JSON object, a string, a number, etc but always in its string representation. e.g. For a system resource, the content will be a stringified YAML descriptor.',  # noqa: E501
    )
    policy: str = Field(
        ...,
        description='Policy written in natural language which will be applied by the LLM to the content of the resource.',  # noqa: E501
    )
    resourceId: str = Field(
        ..., description='A unique Resource Identifier inside the Witboost platform.'
    )
    resourceType: str = Field(
        ...,
        description="Resource type that is being sent in the content. This has to be agreed between the LLM Engine implementation and the platform's registered resource types.",  # noqa: E501
    )


class PolicyResult(BaseModel):
    satisfiesPolicy: bool = Field(
        ...,
        description='Whether the input resource is said to satisfy the policy or not.',
    )
    details: Optional[Dict[str, Any]] = Field(
        None,
        description='A free-form field of additional information linked to the policy result. This will be visible in the Witboost UI as a JSON object.',  # noqa: E501
    )
    errors: List[str] = Field(
        ...,
        description='A list of errors explaining why the resource is not compliant to the policy.',
    )


class ValidationError(BaseModel):
    error: str


class SysError(BaseModel):
    error: str
