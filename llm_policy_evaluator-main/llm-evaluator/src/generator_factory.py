import importlib
from typing import List

from haystack import Pipeline
from haystack.components.builders import ChatPromptBuilder
from haystack.core.component import Component
from haystack.dataclasses import ChatMessage

from src.llm_config import ChatGeneratorSettings
from haystack.utils import Secret
from openai import BadRequestError

import os

SYSTEM_PROMPT = (
    "You are a JSON generator. Reply with ONLY one valid JSON object, "
            "no markdown, no code fences, no explanations. "
            "Return exactly this schema:\n"
            "{\"satisfiesPolicy\": true|false, "
            "\"details\": {\"suggestion\": string, \"elapsedTime\": number}, "
            "\"errors\": [string]}"
)


class GeneratorNotFound(Exception):
    """Raised when a generator has not been found"""
    def __init__(self, class_name):
        self.message = (f'Generator \"{class_name}\" not found. '
                        f'Check the configuration and ensure you defined a supported chat generator engine.')
        super().__init__(self.message)



# Modelli che NON accettano 'system' (es. Mistral Instruct su LM Studio)
ROLE_POLICY = {
    "mistral-7b-instruct-v0.3": "user_only",
}

def _flatten_messages_for_lmstudio(messages):
    """Rimuove 'system' e li concatena nel primo 'user'."""
    if not messages:
        return messages
    sys_txts = []
    new_msgs = []
    for m in messages:
        role = m.get("role")
        content = m.get("content")
        if role == "system":
            # content può essere stringa o lista di part (OpenAI format)
            if isinstance(content, list):
                text_parts = [p.get("text","") for p in content if isinstance(p, dict) and p.get("type")=="text"]
                content = "\n".join(text_parts)
            sys_txts.append(content or "")
        else:
            new_msgs.append(m)

    if not sys_txts:
        return new_msgs

    sys_block = "\n".join([s for s in sys_txts if s]).strip()
    if new_msgs and new_msgs[0].get("role") == "user":
        uc = new_msgs[0].get("content") or ""
        new_msgs[0]["content"] = (sys_block + ("\n\n"+uc if uc else "")).strip()
    else:
        new_msgs.insert(0, {"role": "user", "content": sys_block})
    return new_msgs


class _ChatCompletionsProxy:
    def __init__(self, inner_completions, model_name: str):
        self._inner = inner_completions
        self._policy = ROLE_POLICY.get(model_name, "openai_default")

    def create(self, **kwargs):
        # forzo il fold SOLO se richiesto dalla policy o da env override
        env_override = os.getenv("OPENAI_SUPPORTS_SYSTEM_ROLE", "").lower()
        must_fold = (self._policy == "user_only")
        if env_override in ("true", "false"):
            must_fold = (env_override == "false")

        if must_fold:
            msgs = kwargs.get("messages") or []
            kwargs["messages"] = _flatten_messages_for_lmstudio(msgs)

        try:
            return self._inner.create(**kwargs)
        except BadRequestError as e:
            # safety retry in caso il server continui a rifiutare i system
            if "Only user and assistant roles are supported" in str(e):
                msgs = kwargs.get("messages") or []
                kwargs["messages"] = _flatten_messages_for_lmstudio(msgs)
                return self._inner.create(**kwargs)
            raise


class _ChatProxy:
    def __init__(self, inner_chat, model_name: str):
        self.completions = _ChatCompletionsProxy(inner_chat.completions, model_name)


class _ClientProxy:
    """Proxy dell'OpenAI client: intercetta solo chat.completions.create."""
    def __init__(self, inner_client, model_name: str):
        self._inner = inner_client
        self.chat = _ChatProxy(inner_client.chat, model_name)

    def __getattr__(self, name):
        return getattr(self._inner, name)


def get_chat_generator(chat_generator_settings: ChatGeneratorSettings) -> Component:
    class_name = chat_generator_settings.class_name
    config = chat_generator_settings.config

    if class_name is None:
        raise ValueError('The field "class_name" cannot be None. '
                         'Check the configuration and ensure you defined a supported chat generator engine.')
    if config is None:
        raise ValueError('The field "config" cannot be None. Check the configuration and ensure you defined a proper '
                         'config for the chosen chat generator.')

    modules_as_str = [
        'haystack.components.generators.chat',
        'haystack_integrations.components.generators.amazon_bedrock',
        'haystack_integrations.components.generators.anthropic',
        'haystack_integrations.components.generators.cohere',
        'haystack_integrations.components.generators.google_ai',
        'haystack_integrations.components.generators.mistral',
        'haystack_integrations.components.generators.ollama'
    ]
    modules = [importlib.import_module(module) for module in modules_as_str]
    module = [m for m in modules if hasattr(m, class_name)]
    if not module:
        raise GeneratorNotFound(class_name)

    if class_name == "OpenAIChatGenerator":
        cfg = dict(config)

        # Normalizzo chiave URL (alcuni YAML usano base_url)
        if "api_base_url" not in cfg and "base_url" in cfg:
            cfg["api_base_url"] = cfg.pop("base_url")

        for req in ("api_base_url", "model"):
            if not cfg.get(req):
                raise ValueError(f"Missing required '{req}' in generator config")

        api_key = cfg.get("api_key", os.getenv("OPENAI_API_KEY"))
        if api_key:
            if isinstance(api_key, str):
                cfg["api_key"] = Secret.from_token(api_key)
            else:
                cfg["api_key"] = api_key

        # SOLO dentro generation_kwargs
        gen = dict(cfg.get("generation_kwargs") or {})
        if "max_tokens" not in gen:
            gen["max_tokens"] = 512
        if "temperature" not in gen:
            gen["temperature"] = 0
        cfg["generation_kwargs"] = gen

        # Filtro parametri top-level alle sole chiavi supportate dalla versione corrrente
        allowed_top = {
            "api_key", "model", "streaming_callback", "api_base_url",
            "organization", "generation_kwargs", "timeout", "max_retries",
            "tools", "tools_strict"
        }
        cfg = {k: v for k, v in cfg.items() if k in allowed_top}

        chat_generator_class = getattr(module[0], class_name)
        inst = chat_generator_class(**cfg)

        # annotazioni utili
        resolved_model = cfg.get("model")
        setattr(inst, "_resolved_model_name", resolved_model)
        role_policy = ROLE_POLICY.get(resolved_model, "openai_default")
        setattr(inst, "_role_policy", role_policy)
        setattr(inst, "_supports_system", role_policy != "user_only")

        # >>> NEW: wrappo il client interno se presente <<<
        client_obj = getattr(inst, "client", None)
        if client_obj is not None:
            try:
                wrapped = _ClientProxy(client_obj, resolved_model)
                setattr(inst, "client", wrapped)
            except Exception:
                pass

        return inst
    # --- altri generatori: pass-through ---
    chat_generator_class = getattr(module[0], class_name)
    return chat_generator_class(**{k: v for k, v in config.items() if v is not None})



def get_chat_pipeline(chat_generator: Component, template: List[ChatMessage]) -> Pipeline:
    chat_pipeline = Pipeline()
    full_template = [ChatMessage.from_system(SYSTEM_PROMPT), *template]
    chat_pipeline.add_component('prompt_builder', ChatPromptBuilder(full_template))
    chat_pipeline.add_component('llm', chat_generator)
    chat_pipeline.connect('prompt_builder.prompt', 'llm.messages')
    return chat_pipeline