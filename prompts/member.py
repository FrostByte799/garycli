"""Prompt formatter for member memory."""

from __future__ import annotations

from core.memory import (
    MEMBER_PROMPT_CHAR_LIMIT,
    MEMBER_PROMPT_MAX_DYNAMIC,
    _MEMBER_LOCK,
    _ensure_member_file,
    _split_member_content,
)


def get_member_prompt_section() -> str:
    """Return the trimmed member-memory section injected into the system prompt."""

    # `core.memory` owns persistence and pruning rules. This formatter only
    # consumes its helpers and the persisted markdown artifact.
    with _MEMBER_LOCK:
        path = _ensure_member_file()
        current = path.read_text(encoding="utf-8")
    header, entries = _split_member_content(current)
    pinned = [entry for entry in entries if entry.startswith("### [Pinned]")]
    dynamic = [entry for entry in entries if not entry.startswith("### [Pinned]")]

    selected: list[str] = []
    total = len(header)
    for entry in pinned:
        needed = len(entry) + 2
        if selected and total + needed > MEMBER_PROMPT_CHAR_LIMIT:
            break
        selected.append(entry)
        total += needed

    recent: list[str] = []
    for entry in reversed(dynamic):
        needed = len(entry) + 2
        if recent and (
            total + needed > MEMBER_PROMPT_CHAR_LIMIT or len(recent) >= MEMBER_PROMPT_MAX_DYNAMIC
        ):
            break
        recent.append(entry)
        total += needed
    recent.reverse()
    selected.extend(recent)

    excerpt = header.rstrip()
    if selected:
        excerpt += "\n\n" + "\n\n".join(selected)
    return (
        "## Gary Member Memory（重点）\n"
        "以下内容来自 member.md，是 Gary 的长期经验库。优先复用这些成功经验；"
        "遇到新的高价值经验时，调用 `gary_save_member_memory` 写进去。\n\n"
        f"{excerpt.strip()}"
    )
