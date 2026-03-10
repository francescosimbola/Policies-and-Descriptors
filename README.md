# LLM Engine

- [Overview](#overview)
- [Building](#building)
- [Configuration](#configuration)
- [Running](#running)
- [Testing](#testing)
- [OpenTelemetry Setup](llm-evaluator/docs/opentelemetry.md)
- [Deploying](#deploying)

## Overview

This project provides a LLM Engine to evaluate a System descriptor using a policy written in english by the user from scratch using Python, FastAPI, and Haystack.

### What's a LLM Engine?

A LLM Engine is a microservice which is in charge of evaluating System descriptors using a policy written in english by the user.

### Software stack

This microservice is written in Python 3.11, using FastAPI for the HTTP layer. Project is built with Poetry and supports packaging as Wheel and Docker image, ideal for Kubernetes deployments (which is the preferred option).

## Building

**Requirements:**

- Python 3.11.x (this is a **strict** requirement as of now, due to uvloop 0.17.0)
- Poetry

**Installing**:

To set up a Python environment we use [Poetry](https://python-poetry.org/docs/):

```
curl -sSL https://install.python-poetry.org | python3 -
```

Once Poetry is installed and in your `$PATH`, you can execute the following:

```
poetry --version
```

If you see something like `Poetry (version x.x.x)`, your install is ready to use!

Install the dependencies defined in `llm-evaluator/pyproject.toml`:

```
cd llm-evaluator
poetry install
```

_Note:_ All the following commands are to be run in the Poetry project directory with the virtualenv enabled. If you use _pyenv_ to manage multiple Python runtimes, make sure Poetry is using the right version. You can tell _pyenv_ to use the Python version available in the current shell. Check this Poetry docs page [here](https://python-poetry.org/docs/managing-environments/).

**Type check:** is handled by mypy:

```bash
poetry run mypy src/
```

**Tests:** are handled by pytest:

```bash
poetry run pytest --cov=src/ tests/. --cov-report=xml
```

**Artifacts & Docker image:** the project leverages Poetry for packaging. Build package with:

```
poetry build
```

The Docker image can be built with:

```
docker build .
```

More details can be found [here](llm-evaluator/docs/docker.md).

_Note:_ the version for the project is automatically computed using information gathered from Git, using branch name and tags. Unless you are on a release branch `1.2.x` or a tag `v1.2.3` it will end up being `0.0.0`. You can follow this branch/tag convention or update the version computation to match your preferred strategy.

**CI/CD:** the pipeline is based on GitLab CI as that's what we use internally. It's configured by the `.gitlab-ci.yaml` file in the root of the repository. You can use that as a starting point for your customizations.

## Configuration

### Environment variables

- An environment variable named "MAX_DESCRIPTOR_SIZE_IN_KB" can be used to replace the maximum size in kilobytes of a 
  descriptor to be evaluated by the LLM, which is 10 MB by default. If the size of a descriptor to be evaluated is 
  larger than this value, the descriptor will not be evaluated by the LLM and the policy will be considered failed. The 
  value of this environment variable must be an integer, otherwise an exception occurs.

### Generator

The microservice requires a YAML file `generator.yaml` stored in the `llm-evaluator/config/` folder. 

This file is needed to configure the LLM which will be used to evaluate on whether the data product descriptor adheres the policy or not.

The microservice uses [Haystack Generators](https://docs.haystack.deepset.ai/docs/generators) and the supported generators are:
- [AmazonBedrockChatGenerator](https://docs.haystack.deepset.ai/docs/amazonbedrockchatgenerator)
- [AnthropicChatGenerator](https://docs.haystack.deepset.ai/docs/anthropicchatgenerator)
- [AnthropicVertexChatGenerator](https://docs.haystack.deepset.ai/docs/anthropicvertexchatgenerator)
- [AzureOpenAIChatGenerator](https://docs.haystack.deepset.ai/docs/azureopenaichatgenerator)
- [CohereChatGenerator](https://docs.haystack.deepset.ai/docs/coherechatgenerator)
- [GoogleAIGeminiChatGenerator](https://docs.haystack.deepset.ai/docs/googleaigeminichatgenerator)
- [HuggingFaceAPIChatGenerator](https://docs.haystack.deepset.ai/docs/huggingfaceapichatgenerator)
- [HuggingFaceLocalChatGenerator](https://docs.haystack.deepset.ai/docs/huggingfacelocalchatgenerator)
- [MistralChatGenerator](https://docs.haystack.deepset.ai/docs/mistralchatgenerator)
- [OllamaChatGenerator](https://docs.haystack.deepset.ai/docs/ollamachatgenerator)
- [OpenAIChatGenerator](https://docs.haystack.deepset.ai/docs/openaichatgenerator)

To configure one of them, the `generator.yaml` must contain mandatory:
- The `class_name` field accepts a string that must be precisely equal to the name of one of the supported generators. If this field is written incorrectly, the GeneratorNotFound exception is raised.
- The `config` field, which accepts a Dict[str: Any], will be passed as argument to the chosen generator constructor. If some fields is not accepted by the constructor, an exception is raised. Some parameters are read directly from environment variables when not specified, such as the API key. Read the documentation for the specific generator and configure these parameters using the default environment variables used by the generator constructor.

The config field can be different for each generator. More details on this can be found in the specific generator's documentation.

The following is an example of `generator.yaml` to configure an `AzureOpenAIChatGenerator`:
```yaml
class_name: AzureOpenAIChatGenerator
config:
  azure_endpoint: https://example.openai.azure.com/
  azure_deployment: gpt-4
```
The `api_key` parameter is not specified above because it is stored in an environment variable `AZURE_OPENAI_API_KEY` read by default as written in the AzureOpenAIChatGenerator documentation.

## Running

To run the server locally, use:

```bash
cd llm-evaluator
source $(poetry env info --path)/bin/activate # only needed if venv is not already enabled
bash server_start.sh
```

## Testing
First you have to move in \llm-evaluator in any case:
```
cd llm-evaluator
```

The comands for tests are included in llm-evaluator\tests\integration\scripts\run-tests.cmd.

Then you can run integration tests with Powershell classic comand:
```
.\tests\integration\scripts\run-tests.cmd
```

Also those are the single comands to run local integration tests (conteined in "llm-evaluator\tests\integration\scripts\run-tests.cmd").
```
cd llm-evaluator
$env:OPENAI_API_KEY = "lm-studio"
$env:OPENAI_SUPPORTS_SYSTEM_ROLE = "true"
$env:OPENAI_MAX_RETRIES = "0"
$env:OPENAI_TIMEOUT     = "20"
```
```
py -m poetry run pytest tests/integration/test_policy_evaluator.py -q
```


By default, the server binds to port 8091 on localhost. After it's up and running you can make provisioning requests to this address. You can also check the API documentation served [here](http://127.0.0.1:8091/docs).

## Deploying

This microservice is meant to be deployed to a Kubernetes cluster with the included Helm chart and the scripts that can be found in the `helm` subdirectory. You can find more details [here](helm/README.md).

## License

This project is available under the [Apache License, Version 2.0](https://opensource.org/licenses/Apache-2.0); see [LICENSE](LICENSE) for full details.
