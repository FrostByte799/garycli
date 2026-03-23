"""System prompt construction helpers."""

from __future__ import annotations

from pathlib import Path

from config import DEFAULT_CLOCK

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def _load_template(name: str) -> str:
    """Load a markdown prompt template from disk."""

    return (_TEMPLATES_DIR / name).read_text(encoding="utf-8").strip()


def build_system_prompt(chip: str, language: str, hw_connected: bool) -> str:
    """Build the base system prompt with dynamic runtime context."""

    normalized_language = "en" if str(language).strip().lower().startswith("en") else "zh"
    template_name = "system_en.md" if normalized_language == "en" else "system_zh.md"
    prompt = _load_template(template_name)
    chip_name = (chip or "").strip().upper() or "UNKNOWN"
    if normalized_language == "en":
        prompt += (
            "\n\n## Reply Language\n"
            "- Current CLI language: English.\n"
            "- Reply in English by default, including tool result summaries.\n"
            "- Only switch to Chinese if the user explicitly asks for Chinese."
        )
    else:
        prompt += (
            "\n\n## 回复语言\n"
            "- 当前 CLI 语言：中文。\n"
            "- 默认使用中文回复。\n"
            "- 若用户明确要求英文，或全程使用英文交流，再切换为英文。"
        )
    if normalized_language == "en":
        dynamic = (
            "\n\n## Runtime Context\n"
            f"- Current chip: `{chip_name}`\n"
            f"- Clock source: `{DEFAULT_CLOCK}`\n"
            f"- CLI language: `{normalized_language}`\n"
            f"- Hardware connected: `{str(bool(hw_connected)).lower()}`\n"
            "- If hardware is disconnected, prefer compile-first guidance and state the verification limit clearly."
        )
    else:
        dynamic = (
            "\n\n## 当前运行上下文\n"
            f"- 当前芯片：`{chip_name}`\n"
            f"- 当前时钟源：`{DEFAULT_CLOCK}`\n"
            f"- 当前 CLI 语言：`{normalized_language}`\n"
            f"- 当前硬件连接状态：`{str(bool(hw_connected)).lower()}`\n"
            "- 若硬件未连接，优先走可编译路径，并明确说明无法做运行时验证。"
        )
    return prompt.rstrip() + dynamic
