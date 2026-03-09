# src/template/tmp_basic.py
from src.template.tmp_lmstudio import (
    descriptor_validation,
    policy_validation,
    small_context,
    json_response,
)

messages = [
    f"""{descriptor_validation.strip()}

{policy_validation.strip()}

{small_context.strip()}

{json_response.strip()}
"""
]
