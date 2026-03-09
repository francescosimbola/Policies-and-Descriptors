@echo off
setlocal
set OPENAI_API_KEY=lm-studio
set OPENAI_SUPPORTS_SYSTEM_ROLE=false
set OPENAI_MAX_RETRIES=0
set OPENAI_TIMEOUT=20
poetry run pytest tests\integration\test_policy_evaluator.py -q
endlocal