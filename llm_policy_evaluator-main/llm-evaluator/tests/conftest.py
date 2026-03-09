# conftest.py
import os
import json
import logging
from datetime import datetime
from pathlib import Path
from importlib import resources
import pytest

import pytest
from _pytest.monkeypatch import MonkeyPatch
import httpx

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("openai_payload")
log.setLevel(logging.INFO)

# === Dove salvare i dump completi del prompt ===
PROMPT_DUMPS_DIR = (Path(__file__).resolve().parent / "results" / "prompts")
PROMPT_DUMPS_DIR.mkdir(parents=True, exist_ok=True)



@pytest.fixture(autouse=True)
def _dump_env_from_params(request):
    """
    Per i test parametrizzati con: system_file_name, policy_file_name
    carica i testi reali dai pacchetti test e imposta le env usate dal dumper.
    Così NON devi toccare i test.
    """
    cs = getattr(request.node, "callspec", None)
    if not cs:
        # test non parametrizzato: non accade nulla
        yield
        return

    params = cs.params
    sys_name = params.get("system_file_name")
    pol_name = params.get("policy_file_name")

    # Attiva il dump file
    os.environ["DUMP_LMSTUDIO_INPUT"] = "1"
    os.environ["LMSTUDIO_CALLER"] = "tmp_lmstudio.py"

    # Descriptor (il "system_file_name" è il .yaml)
    if sys_name:
        try:
            with resources.as_file(resources.files("tests.integration.systems") / sys_name) as p:
                os.environ["EVAL_DESCRIPTOR_TEXT"] = p.read_text(encoding="utf-8")
        except Exception:
            # Se i file stanno altrove, si cambia il package sopra
            pass

    # Policy
    if pol_name:
        try:
            with resources.as_file(resources.files("tests.integration.policies") / pol_name) as p:
                os.environ["EVAL_POLICY_TEXT"] = p.read_text(encoding="utf-8")
        except Exception:
            pass

    # Il SYSTEM_PROMPT viene estratto dai messaggi se non viene fornito prima:
    # os.environ["EVAL_SYSTEM_PROMPT"] = "..."  # opzionale

    yield

def _safe_json_loads(raw: bytes | str):
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="ignore")
    try:
        return json.loads(raw)
    except Exception:
        return None

def _head(text_or_obj, limit=500):
    try:
        if isinstance(text_or_obj, (dict, list)):
            s = json.dumps(text_or_obj, ensure_ascii=False)
        else:
            s = str(text_or_obj)
    except Exception:
        s = str(text_or_obj)
    return s[:limit]

def _content_to_text(content) -> str:
    """
    Normalizza il campo 'content' dei messaggi OpenAI:
    - se è stringa, la restituisce
    - se è lista di segmenti (es. [{'type':'text','text':'...'}]) concatena i testi
    - altrimenti stringify.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        buf = []
        for seg in content:
            if isinstance(seg, dict):
                if "text" in seg:
                    buf.append(str(seg.get("text", "")))
                elif "image_url" in seg:
                    buf.append(f"[image_url:{seg.get('image_url')}]")
                else:
                    buf.append(str(seg))
            else:
                buf.append(str(seg))
        return "".join(buf)
    return str(content)

def _render_messages(messages: list | None) -> str:
    parts = []
    for m in (messages or []):
        role = m.get("role", "")
        content = _content_to_text(m.get("content", ""))
        parts.append(f"## {role.upper()}\n{content}")
    return "\n\n".join(parts)

def _extract_system_from_messages(messages: list | None) -> str:
    if not messages:
        return ""
    for m in messages:
        if m.get("role") == "system":
            return _content_to_text(m.get("content", ""))
    return ""

def _dump_payload_file(payload: dict):
    """
    Scrive un file .md con:
      - CALLER (LMSTUDIO_CALLER, default 'tmp_lmstudio.py')
      - SYSTEM_PROMPT (da env o estratto dai messaggi)
      - POLICY (da env)
      - DESCRIPTOR (da env)
      - MESSAGGI FINALI (ruoli + testi)
      - RAW PAYLOAD JSON
    Attivo solo se DUMP_LMSTUDIO_INPUT=1
    """
    if os.getenv("DUMP_LMSTUDIO_INPUT", "0") != "1":
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = PROMPT_DUMPS_DIR / f"lmstudio_input_{ts}.md"

    # Dati opzionali da env (puoi valorizzarli nel test)
    caller         = os.getenv("LMSTUDIO_CALLER", "tmp_lmstudio.py").strip()
    sys_env        = os.getenv("EVAL_SYSTEM_PROMPT", "").strip()
    policy_text    = os.getenv("EVAL_POLICY_TEXT", "").strip()
    descriptor_txt = os.getenv("EVAL_DESCRIPTOR_TEXT", "").strip()

    messages = payload.get("messages", [])
    system_from_msgs = _extract_system_from_messages(messages)
    system_prompt_final = sys_env if sys_env else system_from_msgs

    messages_dump = _render_messages(messages)
    raw_json      = json.dumps(payload, ensure_ascii=False, indent=2)

    doc = "\n\n".join([
        "# LMStudio — Input effettivo inviato",
        f"**Caller**: {caller}",
        "\n---\n\n### SYSTEM_PROMPT\n",
        system_prompt_final or "(vuoto)",
        "\n---\n\n### POLICY\n",
        policy_text or "(vuoto)",
        "\n---\n\n### DESCRIPTOR\n",
        descriptor_txt or "(vuoto)",
        "\n---\n\n### MESSAGGI FINALI (ruoli + contenuti)\n",
        messages_dump or "(nessun messaggio)",
        "\n---\n\n### RAW PAYLOAD JSON\n",
        raw_json
    ])

    out_path.write_text(doc, encoding="utf-8")
    print(f"[dump] LMStudio input salvato in: {out_path}")

@pytest.fixture(autouse=True, scope="session")
def log_openai_payload():
    """
    Intercetta httpx.Client.send e logga il payload delle chiamate a /chat/completions.
    In più, se DUMP_LMSTUDIO_INPUT=1, salva un file .md con l'input completo.
    """
    mp = MonkeyPatch()
    original_send = httpx.Client.send

    def wrapped_send(self, request: httpx.Request, *args, **kwargs):
        try:
            if request.url.path.endswith("/chat/completions") and request.method.upper() == "POST":
                payload = _safe_json_loads(request.content)  # body JSON della POST
                snapshot = {}
                if isinstance(payload, dict):
                    # Parametri interessanti
                    for k in ("model", "temperature", "max_tokens", "max_completion_tokens", "stop", "response_format"):
                        if k in payload:
                            snapshot[k] = payload[k]

                    # Messaggi (preview per console)
                    msgs = payload.get("messages")
                    if isinstance(msgs, list):
                        preview = []
                        for m in msgs:
                            role = m.get("role")
                            content = m.get("content", "")
                            content_text = _content_to_text(content)
                            preview.append({
                                "role": role,
                                "content_len": len(content_text),
                                "content_head": _head(content_text, 500)
                            })
                        snapshot["messages_count"] = len(msgs)
                        snapshot["messages_preview"] = preview

                    # Dump completo su file (se abilitato)
                    _dump_payload_file(payload)

                log.info("OPENAI /chat/completions payload:\n%s",
                         json.dumps(snapshot, ensure_ascii=False, indent=2))
        except Exception as e:
            log.warning("Failed to log OpenAI payload: %s", e)

        return original_send(self, request, *args, **kwargs)

    mp.setattr(httpx.Client, "send", wrapped_send, raising=True)
    try:
        yield
    finally:
        mp.undo()
