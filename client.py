"""OpenAI client management and AI configuration helpers."""

from __future__ import annotations

import base64
import importlib
import json
import mimetypes
import re
from pathlib import Path
from typing import Any, Optional

import config as _cfg

_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _ROOT / "config.py"

_AI_PRESETS = [
    ("OpenAI", "https://api.openai.com/v1", "gpt-4o"),
    ("DeepSeek", "https://api.deepseek.com/v1", "deepseek-chat"),
    ("Kimi / Moonshot", "https://api.moonshot.cn/v1", "kimi-k2.5"),
    (
        "Google Gemini",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
        "gemini-2.0-flash",
    ),
    ("通义千问 (阿里云)", "https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-plus"),
    ("智谱 GLM", "https://open.bigmodel.cn/api/paas/v4/", "glm-4-flash"),
    ("Ollama (本地)", "http://127.0.0.1:11434/v1", "qwen2.5-coder:14b"),
    ("自定义 / Other", "", ""),
]

_CONFIG_KEYS_TO_RELOAD = (
    "AI_API_KEY",
    "AI_BASE_URL",
    "AI_MODEL",
    "AI_TEMPERATURE",
    "DEFAULT_CHIP",
    "DEFAULT_CLOCK",
    "CLI_LANGUAGE",
    "SERIAL_PORT",
    "SERIAL_BAUD",
    "POST_FLASH_DELAY",
    "REGISTER_READ_DELAY",
)

AI_API_KEY = getattr(_cfg, "AI_API_KEY", "")
AI_BASE_URL = getattr(_cfg, "AI_BASE_URL", "https://api.openai.com/v1")
AI_MODEL = getattr(_cfg, "AI_MODEL", "gpt-4o")
AI_TEMPERATURE = getattr(_cfg, "AI_TEMPERATURE", 1)
DEFAULT_CHIP = getattr(_cfg, "DEFAULT_CHIP", "")
DEFAULT_CLOCK = getattr(_cfg, "DEFAULT_CLOCK", "HSI_internal")
CLI_LANGUAGE = getattr(_cfg, "CLI_LANGUAGE", "zh")
SERIAL_PORT = getattr(_cfg, "SERIAL_PORT", "")
SERIAL_BAUD = getattr(_cfg, "SERIAL_BAUD", 115200)
POST_FLASH_DELAY = getattr(_cfg, "POST_FLASH_DELAY", 1.5)
REGISTER_READ_DELAY = getattr(_cfg, "REGISTER_READ_DELAY", 0.3)

_AI_CLIENT: Any | None = None
_AI_CLIENT_SIGNATURE: tuple[str, str, float] | None = None
_VISION_MODEL_HINTS = (
    "gpt-4o",
    "gpt-4.1",
    "gpt-4.5",
    "o1",
    "o3",
    "vision",
    "vl",
    "gemini",
    "kimi",
    "qwen-vl",
    "glm-4v",
    "internvl",
    "llava",
    "minicpm-v",
)


def _load_openai_class() -> Any | None:
    """Import and return the OpenAI client class when available."""

    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        return None
    return OpenAI


def _parse_cli_language(value: Any, default: Optional[str] = None) -> Optional[str]:
    """Normalize CLI language aliases to `en` or `zh`."""

    raw = str(value or "").strip().lower()
    if not raw:
        return default
    if raw in {"en", "eng", "english", "英文"}:
        return "en"
    if raw in {"zh", "cn", "zh-cn", "zh_cn", "chinese", "中文"}:
        return "zh"
    return None


def _normalize_cli_language(value: Any) -> str:
    """Return a safe CLI language code."""

    return _parse_cli_language(value, default="zh") or "zh"


CLI_LANGUAGE = _normalize_cli_language(CLI_LANGUAGE)


def _current_settings() -> dict[str, Any]:
    """Return the current runtime configuration snapshot."""

    return {
        "AI_API_KEY": AI_API_KEY,
        "AI_BASE_URL": AI_BASE_URL,
        "AI_MODEL": AI_MODEL,
        "AI_TEMPERATURE": AI_TEMPERATURE,
        "DEFAULT_CHIP": DEFAULT_CHIP,
        "DEFAULT_CLOCK": DEFAULT_CLOCK,
        "CLI_LANGUAGE": CLI_LANGUAGE,
        "SERIAL_PORT": SERIAL_PORT,
        "SERIAL_BAUD": SERIAL_BAUD,
        "POST_FLASH_DELAY": POST_FLASH_DELAY,
        "REGISTER_READ_DELAY": REGISTER_READ_DELAY,
    }


def _upsert_config_assignment(text: str, key: str, value: Any) -> str:
    """Insert or replace a single assignment in `config.py` text."""

    line = f"{key} = {json.dumps(value, ensure_ascii=False)}"
    pattern = rf"^{key}\s*=.*$"
    if re.search(pattern, text, re.MULTILINE):
        return re.sub(pattern, line, text, flags=re.MULTILINE)
    if text and not text.endswith("\n"):
        text += "\n"
    return text + line + "\n"


def _read_ai_config() -> tuple[str, str, str]:
    """Read `(api_key, base_url, model)` from `config.py`."""

    if not _CONFIG_PATH.exists():
        return AI_API_KEY, AI_BASE_URL, AI_MODEL
    text = _CONFIG_PATH.read_text(encoding="utf-8")

    def _get(pattern: str) -> str:
        match = re.search(pattern, text, re.MULTILINE)
        return match.group(1).strip() if match else ""

    return (
        _get(r'^AI_API_KEY\s*=\s*["\']([^"\']*)["\']') or AI_API_KEY,
        _get(r'^AI_BASE_URL\s*=\s*["\']([^"\']*)["\']') or AI_BASE_URL,
        _get(r'^AI_MODEL\s*=\s*["\']([^"\']*)["\']') or AI_MODEL,
    )


def _write_config_assignments(updates: dict[str, Any]) -> bool:
    """Update multiple assignments in `config.py` in place."""

    if not _CONFIG_PATH.exists():
        return False
    text = _CONFIG_PATH.read_text(encoding="utf-8")
    for key, value in updates.items():
        text = _upsert_config_assignment(text, key, value)
    _CONFIG_PATH.write_text(text, encoding="utf-8")
    return True


def _write_ai_config(api_key: str, base_url: str, model: str) -> bool:
    """Persist the core AI settings to `config.py`."""

    return _write_config_assignments(
        {
            "AI_API_KEY": api_key,
            "AI_BASE_URL": base_url,
            "AI_MODEL": model,
        }
    )


def _write_cli_language_config(language: str) -> bool:
    """Persist the CLI language to `config.py`."""

    return _write_config_assignments({"CLI_LANGUAGE": _normalize_cli_language(language)})


def _reload_ai_globals() -> dict[str, Any]:
    """Reload runtime settings from `config.py` and invalidate the cached client if needed."""

    global AI_API_KEY
    global AI_BASE_URL
    global AI_MODEL
    global AI_TEMPERATURE
    global DEFAULT_CHIP
    global DEFAULT_CLOCK
    global CLI_LANGUAGE
    global SERIAL_PORT
    global SERIAL_BAUD
    global POST_FLASH_DELAY
    global REGISTER_READ_DELAY
    global _AI_CLIENT
    global _AI_CLIENT_SIGNATURE

    previous_signature = (AI_API_KEY, AI_BASE_URL)
    importlib.reload(_cfg)
    defaults = {
        "AI_API_KEY": "",
        "AI_BASE_URL": "https://api.openai.com/v1",
        "AI_MODEL": "gpt-4o",
        "AI_TEMPERATURE": 1,
        "DEFAULT_CHIP": "",
        "DEFAULT_CLOCK": "HSI_internal",
        "CLI_LANGUAGE": "zh",
        "SERIAL_PORT": "",
        "SERIAL_BAUD": 115200,
        "POST_FLASH_DELAY": 1.5,
        "REGISTER_READ_DELAY": 0.3,
    }
    for name in _CONFIG_KEYS_TO_RELOAD:
        globals()[name] = getattr(_cfg, name, defaults[name])
    CLI_LANGUAGE = _normalize_cli_language(CLI_LANGUAGE)
    if (AI_API_KEY, AI_BASE_URL) != previous_signature:
        _AI_CLIENT = None
        _AI_CLIENT_SIGNATURE = None
    return _current_settings()


def reload_ai_config() -> dict[str, Any]:
    """Public wrapper for reloading AI/runtime settings."""

    return _reload_ai_globals()


def _mask_key(key: str) -> str:
    """Mask a secret for CLI display."""

    if not key:
        return "(未设置)"
    return key[:6] + "..." + key[-4:] if len(key) > 12 else "***"


def _api_key_is_placeholder(api_key: str) -> bool:
    """Return whether the API key is empty or still using a template value."""

    key = (api_key or "").strip()
    if not key:
        return True
    placeholder_prefixes = ("YOUR_API_KEY", "sk-YOUR")
    return any(key.startswith(prefix) for prefix in placeholder_prefixes)


def _ai_is_configured() -> bool:
    """Return whether the runtime has a usable AI configuration."""

    api_key, base_url, model = _read_ai_config()
    return bool(api_key and base_url and model and not _api_key_is_placeholder(api_key))


def get_ai_client(timeout: float = 180.0, force_reload: bool = False) -> Any | None:
    """Return a lazily-created OpenAI-compatible client for the current config."""

    global _AI_CLIENT
    global _AI_CLIENT_SIGNATURE

    openai_class = _load_openai_class()
    if openai_class is None:
        return None

    signature = (AI_API_KEY, AI_BASE_URL, float(timeout))
    if force_reload:
        _AI_CLIENT = None
        _AI_CLIENT_SIGNATURE = None
    if _AI_CLIENT is None or _AI_CLIENT_SIGNATURE != signature:
        _AI_CLIENT = openai_class(api_key=AI_API_KEY, base_url=AI_BASE_URL, timeout=timeout)
        _AI_CLIENT_SIGNATURE = signature
    return _AI_CLIENT


def model_may_support_vision(model: Optional[str] = None) -> bool:
    """Return whether the configured model name looks vision-capable."""

    name = str(model or AI_MODEL or "").strip().lower()
    if not name:
        return False
    return any(hint in name for hint in _VISION_MODEL_HINTS)


def build_image_message_part(image_path: str | Path) -> dict[str, Any]:
    """Build an OpenAI-compatible image content part from a local image path."""

    path = Path(image_path).expanduser().resolve()
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    if not mime.startswith("image/"):
        raise ValueError(f"Unsupported image MIME type: {mime}")
    image_b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return {
        "type": "image_url",
        "image_url": {
            "url": f"data:{mime};base64,{image_b64}",
        },
    }


def build_vision_message_parts(image_path: str | Path, prompt: str) -> list[dict[str, Any]]:
    """Build a provider-agnostic OpenAI-compatible multimodal user content payload."""

    return [
        build_image_message_part(image_path),
        {
            "type": "text",
            "text": prompt,
        },
    ]


def stream_chat(
    *,
    messages: list[dict[str, Any]],
    tools: Optional[list[dict[str, Any]]] = None,
    tool_choice: str | dict[str, Any] = "auto",
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    client: Any | None = None,
    timeout: float = 180.0,
) -> Any:
    """Create a streaming chat completion request using the current runtime config."""

    active_client = client or get_ai_client(timeout=timeout)
    if active_client is None:
        raise RuntimeError("openai 未安装: pip install openai")
    request: dict[str, Any] = {
        "model": model or AI_MODEL,
        "messages": messages,
        "temperature": AI_TEMPERATURE if temperature is None else temperature,
        "stream": True,
    }
    if tools is not None:
        request["tools"] = tools
        request["tool_choice"] = tool_choice
    return active_client.chat.completions.create(**request)


__all__ = [
    "AI_API_KEY",
    "AI_BASE_URL",
    "AI_MODEL",
    "AI_TEMPERATURE",
    "CLI_LANGUAGE",
    "DEFAULT_CHIP",
    "DEFAULT_CLOCK",
    "POST_FLASH_DELAY",
    "REGISTER_READ_DELAY",
    "SERIAL_BAUD",
    "SERIAL_PORT",
    "_AI_PRESETS",
    "_ai_is_configured",
    "_api_key_is_placeholder",
    "_mask_key",
    "_read_ai_config",
    "_reload_ai_globals",
    "_write_ai_config",
    "_write_cli_language_config",
    "build_image_message_part",
    "build_vision_message_parts",
    "get_ai_client",
    "model_may_support_vision",
    "reload_ai_config",
    "stream_chat",
]
