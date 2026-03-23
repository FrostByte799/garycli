"""Telegram bot integration for Gary CLI."""

from __future__ import annotations

import atexit
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional, Protocol

import requests
from rich.console import Console

GARY_HOME = Path.home() / ".gary"
TELEGRAM_CONFIG_PATH = GARY_HOME / "telegram_bot.json"
TELEGRAM_PID_PATH = GARY_HOME / "telegram_bot.pid"
TELEGRAM_LOG_PATH = GARY_HOME / "telegram_bot.log"
TELEGRAM_MESSAGE_LIMIT = 3800
_TELEGRAM_CONFIG_LOCK = threading.RLock()


class TelegramAgent(Protocol):
    """Protocol for chat agents used by the Telegram bridge."""

    def refresh_ai_client(self) -> None:
        """Refresh the runtime AI client."""

    def chat(
        self,
        user_input: str,
        stream_to_console: bool = True,
        text_callback: Optional[Callable[[str], None]] = None,
        tool_callback: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> str:
        """Handle a chat turn and return the final reply."""


@dataclass
class TelegramHooks:
    """Runtime callbacks injected from stm32_agent.py."""

    console: Optional[Console] = None
    cli_text: Optional[Callable[[str, str], str]] = None
    is_ai_configured: Optional[Callable[[], bool]] = None
    configure_ai_cli: Optional[Callable[[], Any]] = None
    agent_factory: Optional[Callable[..., TelegramAgent]] = None
    hardware_status: Optional[Callable[[], dict[str, Any]]] = None
    connect: Optional[Callable[[Optional[str]], dict[str, Any]]] = None
    disconnect: Optional[Callable[[], dict[str, Any]]] = None
    set_chip: Optional[Callable[[str], dict[str, Any]]] = None
    list_projects: Optional[Callable[[], dict[str, Any]]] = None
    detect_serial_ports: Optional[Callable[..., list[str]]] = None
    serial_connect: Optional[Callable[[Optional[str], Optional[int]], dict[str, Any]]] = None
    get_current_chip: Optional[Callable[[], str]] = None
    script_path: Optional[Path] = None
    workdir: Optional[Path] = None


_HOOKS = TelegramHooks()


def configure_telegram_integration(
    *,
    console: Console,
    cli_text: Callable[[str, str], str],
    is_ai_configured: Callable[[], bool],
    configure_ai_cli: Callable[[], Any],
    agent_factory: Callable[..., TelegramAgent],
    hardware_status: Callable[[], dict[str, Any]],
    connect: Callable[[Optional[str]], dict[str, Any]],
    disconnect: Callable[[], dict[str, Any]],
    set_chip: Callable[[str], dict[str, Any]],
    list_projects: Callable[[], dict[str, Any]],
    detect_serial_ports: Callable[..., list[str]],
    serial_connect: Callable[[Optional[str], Optional[int]], dict[str, Any]],
    get_current_chip: Callable[[], str],
    script_path: Path,
    workdir: Path,
) -> None:
    """Install runtime hooks required by the Telegram integration."""

    global _HOOKS
    _HOOKS = TelegramHooks(
        console=console,
        cli_text=cli_text,
        is_ai_configured=is_ai_configured,
        configure_ai_cli=configure_ai_cli,
        agent_factory=agent_factory,
        hardware_status=hardware_status,
        connect=connect,
        disconnect=disconnect,
        set_chip=set_chip,
        list_projects=list_projects,
        detect_serial_ports=detect_serial_ports,
        serial_connect=serial_connect,
        get_current_chip=get_current_chip,
        script_path=script_path,
        workdir=workdir,
    )


def _console() -> Console:
    """Return the configured console instance."""

    if _HOOKS.console is None:
        raise RuntimeError("Telegram integration is not configured: console is missing")
    return _HOOKS.console


def _cli_text(zh: str, en: str) -> str:
    """Return localized CLI text using the injected language helper."""

    if _HOOKS.cli_text is None:
        raise RuntimeError("Telegram integration is not configured: cli_text is missing")
    return _HOOKS.cli_text(zh, en)


def _is_ai_configured() -> bool:
    """Return whether the AI client is configured."""

    if _HOOKS.is_ai_configured is None:
        raise RuntimeError(
            "Telegram integration is not configured: is_ai_configured is missing"
        )
    return bool(_HOOKS.is_ai_configured())


def _agent_factory() -> Callable[..., TelegramAgent]:
    """Return the configured agent factory."""

    if _HOOKS.agent_factory is None:
        raise RuntimeError("Telegram integration is not configured: agent_factory is missing")
    return _HOOKS.agent_factory


def _hardware_status() -> dict[str, Any]:
    """Return the current STM32 hardware status."""

    if _HOOKS.hardware_status is None:
        raise RuntimeError(
            "Telegram integration is not configured: hardware_status is missing"
        )
    return _HOOKS.hardware_status()


def _connect(chip: Optional[str]) -> dict[str, Any]:
    """Connect hardware using the injected STM32 callback."""

    if _HOOKS.connect is None:
        raise RuntimeError("Telegram integration is not configured: connect is missing")
    return _HOOKS.connect(chip)


def _disconnect() -> dict[str, Any]:
    """Disconnect hardware using the injected STM32 callback."""

    if _HOOKS.disconnect is None:
        raise RuntimeError("Telegram integration is not configured: disconnect is missing")
    return _HOOKS.disconnect()


def _set_chip(chip: str) -> dict[str, Any]:
    """Switch the active chip using the injected STM32 callback."""

    if _HOOKS.set_chip is None:
        raise RuntimeError("Telegram integration is not configured: set_chip is missing")
    return _HOOKS.set_chip(chip)


def _list_projects() -> dict[str, Any]:
    """List recent projects using the injected STM32 callback."""

    if _HOOKS.list_projects is None:
        raise RuntimeError("Telegram integration is not configured: list_projects is missing")
    return _HOOKS.list_projects()


def _detect_serial_ports() -> list[str]:
    """Detect available serial ports."""

    if _HOOKS.detect_serial_ports is None:
        raise RuntimeError(
            "Telegram integration is not configured: detect_serial_ports is missing"
        )
    return _HOOKS.detect_serial_ports()


def _serial_connect(port: Optional[str], baud: Optional[int]) -> dict[str, Any]:
    """Connect a serial port using the injected STM32 callback."""

    if _HOOKS.serial_connect is None:
        raise RuntimeError(
            "Telegram integration is not configured: serial_connect is missing"
        )
    return _HOOKS.serial_connect(port, baud)


def _current_chip() -> str:
    """Return the current chip name for Telegram status output."""

    if _HOOKS.get_current_chip is None:
        raise RuntimeError(
            "Telegram integration is not configured: get_current_chip is missing"
        )
    return _HOOKS.get_current_chip()


def _script_path() -> Path:
    """Return the CLI entry script path used by the daemon launcher."""

    if _HOOKS.script_path is None:
        raise RuntimeError("Telegram integration is not configured: script_path is missing")
    return _HOOKS.script_path


def _workdir() -> Path:
    """Return the CLI working directory used by the daemon launcher."""

    if _HOOKS.workdir is None:
        raise RuntimeError("Telegram integration is not configured: workdir is missing")
    return _HOOKS.workdir


def _ensure_gary_home() -> None:
    """Create the shared Gary home directory when missing."""

    GARY_HOME.mkdir(parents=True, exist_ok=True)


def _default_telegram_config() -> dict[str, Any]:
    """Return the default Telegram configuration structure."""

    return {
        "bot_token": "",
        "bot_id": None,
        "bot_username": "",
        "bot_name": "",
        "allow_all_chats": False,
        "allowed_chat_ids": [],
        "allowed_user_ids": [],
        "last_update_id": 0,
        "updated_at": "",
    }


def _unique_int_list(values: Any) -> list[int]:
    """Normalize a sequence into a unique ordered integer list."""

    result: list[int] = []
    seen: set[int] = set()
    for value in values or []:
        try:
            num = int(str(value).strip())
        except (TypeError, ValueError):
            continue
        if num in seen:
            continue
        seen.add(num)
        result.append(num)
    return result


def _normalize_telegram_config(config: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Normalize a raw Telegram config dictionary."""

    merged = _default_telegram_config()
    if isinstance(config, dict):
        merged.update(config)
    merged["allow_all_chats"] = bool(merged.get("allow_all_chats", False))
    merged["allowed_chat_ids"] = _unique_int_list(merged.get("allowed_chat_ids"))
    merged["allowed_user_ids"] = _unique_int_list(merged.get("allowed_user_ids"))
    try:
        merged["last_update_id"] = int(merged.get("last_update_id", 0) or 0)
    except (TypeError, ValueError):
        merged["last_update_id"] = 0
    return merged


def _read_telegram_config() -> dict[str, Any]:
    """Read the Telegram bot config from disk."""

    with _TELEGRAM_CONFIG_LOCK:
        if not TELEGRAM_CONFIG_PATH.exists():
            return _default_telegram_config()
        try:
            raw = json.loads(TELEGRAM_CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return _default_telegram_config()
        return _normalize_telegram_config(raw)


def _write_telegram_config(config: dict[str, Any]) -> dict[str, Any]:
    """Persist a normalized Telegram bot config to disk."""

    with _TELEGRAM_CONFIG_LOCK:
        _ensure_gary_home()
        clean = _normalize_telegram_config(config)
        clean["updated_at"] = datetime.now().isoformat(timespec="seconds")
        TELEGRAM_CONFIG_PATH.write_text(
            json.dumps(clean, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return clean


def telegram_is_configured(config: Optional[dict[str, Any]] = None) -> bool:
    """Return whether a usable Telegram bot token is configured."""

    config = config or _read_telegram_config()
    token = str(config.get("bot_token", "")).strip()
    placeholders = ("", "YOUR_TELEGRAM_BOT_TOKEN", "123456:ABC")
    return bool(token and token not in placeholders and ":" in token)


def _mask_telegram_token(token: str) -> str:
    """Hide most of the Telegram bot token for CLI display."""

    if not token:
        return "(未设置)"
    return token[:8] + "..." + token[-6:] if len(token) > 20 else "***"


def _split_tokens(raw: str) -> list[str]:
    """Split a CLI token list on spaces or commas."""

    return [tok for tok in re.split(r"[\s,]+", raw.strip()) if tok]


def _parse_telegram_targets(raw: str) -> dict[str, list[int] | list[str]]:
    """Parse `chat_id` and `user:id` targets from CLI input."""

    parsed: dict[str, list[int] | list[str]] = {
        "chat_ids": [],
        "user_ids": [],
        "invalid": [],
    }
    for token in _split_tokens(raw):
        kind = "chat"
        value = token
        lower = token.lower()
        if lower.startswith("user:"):
            kind, value = "user", token.split(":", 1)[1]
        elif lower.startswith("chat:"):
            kind, value = "chat", token.split(":", 1)[1]
        try:
            num = int(value)
        except ValueError:
            parsed["invalid"].append(token)
            continue
        if kind == "user":
            parsed["user_ids"].append(num)
        else:
            parsed["chat_ids"].append(num)
    parsed["chat_ids"] = _unique_int_list(parsed["chat_ids"])
    parsed["user_ids"] = _unique_int_list(parsed["user_ids"])
    return parsed


def get_telegram_target_candidates() -> list[str]:
    """Return completion candidates for Telegram allow/remove commands."""

    config = _read_telegram_config()
    candidates = [str(v) for v in config.get("allowed_chat_ids", [])]
    candidates.extend(f"user:{v}" for v in config.get("allowed_user_ids", []))
    if "user:" not in candidates:
        candidates.append("user:")
    return candidates


def _telegram_set_permissions(
    *,
    add_chat_ids: Optional[list[int]] = None,
    remove_chat_ids: Optional[list[int]] = None,
    add_user_ids: Optional[list[int]] = None,
    remove_user_ids: Optional[list[int]] = None,
    allow_all_chats: Optional[bool] = None,
) -> dict[str, Any]:
    """Update Telegram whitelist settings and persist them."""

    config = _read_telegram_config()
    chats = set(config.get("allowed_chat_ids", []))
    users = set(config.get("allowed_user_ids", []))
    chats.update(add_chat_ids or [])
    users.update(add_user_ids or [])
    chats.difference_update(remove_chat_ids or [])
    users.difference_update(remove_user_ids or [])
    config["allowed_chat_ids"] = sorted(chats)
    config["allowed_user_ids"] = sorted(users)
    if allow_all_chats is not None:
        config["allow_all_chats"] = bool(allow_all_chats)
    return _write_telegram_config(config)


def _read_pid_file() -> Optional[int]:
    """Read the Telegram daemon PID file."""

    try:
        return int(TELEGRAM_PID_PATH.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def _pid_is_alive(pid: Optional[int]) -> bool:
    """Return whether a process still exists and is not a zombie."""

    if not pid:
        return False
    proc_stat = Path(f"/proc/{pid}/stat")
    if proc_stat.exists():
        try:
            stat_text = proc_stat.read_text(encoding="utf-8", errors="ignore")
            fields = stat_text.split()
            if len(fields) >= 3 and fields[2] == "Z":
                return False
            return True
        except Exception:
            pass
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _write_pid_file(pid: int) -> None:
    """Write the Telegram daemon PID file."""

    _ensure_gary_home()
    TELEGRAM_PID_PATH.write_text(str(pid), encoding="utf-8")


def _clear_pid_file(expected_pid: Optional[int] = None) -> None:
    """Remove the Telegram PID file when it matches the expected PID."""

    if not TELEGRAM_PID_PATH.exists():
        return
    if expected_pid is not None:
        current = _read_pid_file()
        if current and current != expected_pid:
            return
    try:
        TELEGRAM_PID_PATH.unlink()
    except FileNotFoundError:
        pass


def _telegram_daemon_status() -> dict[str, Any]:
    """Return daemon running state, PID, and log path."""

    pid = _read_pid_file()
    running = _pid_is_alive(pid)
    if pid and not running:
        _clear_pid_file(pid)
        pid = None
    return {
        "running": running,
        "pid": pid,
        "log_path": str(TELEGRAM_LOG_PATH),
    }


def _telegram_api_call(
    token: str,
    method: str,
    payload: Optional[dict[str, Any]] = None,
    timeout: float = 30.0,
) -> Any:
    """Call the Telegram Bot API and return the `result` payload."""

    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        response = requests.post(url, json=payload or {}, timeout=timeout)
    except requests.RequestException as exc:
        raise RuntimeError(f"Telegram API 网络错误: {exc}") from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"Telegram API 返回非法 JSON: HTTP {response.status_code}"
        ) from exc

    if response.status_code >= 400 or not data.get("ok"):
        detail = data.get("description") or response.text[:200] or f"HTTP {response.status_code}"
        raise RuntimeError(f"Telegram API 调用失败: {detail}")
    return data.get("result")


def _telegram_get_me(token: str) -> dict[str, Any]:
    """Validate a bot token and return basic bot metadata."""

    result = _telegram_api_call(token, "getMe", timeout=15.0)
    return result if isinstance(result, dict) else {}


def _telegram_set_my_commands(token: str) -> None:
    """Register the Telegram command menu for the Gary bot."""

    commands = [
        {"command": "start", "description": "查看 Gary 机器人状态和用法"},
        {"command": "help", "description": "查看 Telegram 侧命令"},
        {"command": "clear", "description": "清空当前聊天上下文"},
        {"command": "status", "description": "查看 Gary 当前硬件状态"},
        {"command": "connect", "description": "连接探针和串口，可带芯片型号"},
        {"command": "disconnect", "description": "断开当前硬件连接"},
        {"command": "chip", "description": "查看或切换芯片型号"},
        {"command": "projects", "description": "查看最近历史项目"},
    ]
    _telegram_api_call(token, "setMyCommands", {"commands": commands}, timeout=20.0)


def _telegram_split_text(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    """Split a long Telegram reply into safe-sized chunks."""

    source = (text or "").strip() or "Gary 已处理，但没有返回文本。"
    chunks: list[str] = []
    while len(source) > limit:
        cut = source.rfind("\n\n", 0, limit)
        if cut < limit // 3:
            cut = source.rfind("\n", 0, limit)
        if cut < limit // 3:
            cut = source.rfind(" ", 0, limit)
        if cut < limit // 3:
            cut = limit
        chunks.append(source[:cut].rstrip())
        source = source[cut:].lstrip()
    if source:
        chunks.append(source)
    return chunks


def _telegram_send_text(
    token: str,
    chat_id: int,
    text: str,
    reply_to_message_id: Optional[int] = None,
) -> None:
    """Send a possibly long text reply to Telegram."""

    for index, chunk in enumerate(_telegram_split_text(text)):
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": chunk,
            "disable_web_page_preview": True,
        }
        if index == 0 and reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        _telegram_api_call(token, "sendMessage", payload, timeout=20.0)


def telegram_log(message: str) -> None:
    """Append a line to the Telegram integration log."""

    try:
        _ensure_gary_home()
        with TELEGRAM_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(f"[{datetime.now().isoformat(timespec='seconds')}] {message}\n")
    except Exception:
        pass


def _telegram_send_chat_action(token: str, chat_id: int, action: str = "typing") -> None:
    """Send a chat action such as `typing` to Telegram."""

    _telegram_api_call(
        token,
        "sendChatAction",
        {"chat_id": chat_id, "action": action},
        timeout=10.0,
    )


class _TelegramTypingPulse:
    """Background heartbeat that keeps Telegram showing `typing`."""

    def __init__(self, token: str, chat_id: int, interval: float = 4.0) -> None:
        """Initialize the typing pulse."""

        self.token = token
        self.chat_id = chat_id
        self.interval = interval
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def __enter__(self) -> "_TelegramTypingPulse":
        """Start the typing pulse when entering the context."""

        self.start()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        """Stop the typing pulse when leaving the context."""

        self.stop()

    def start(self) -> None:
        """Start the typing pulse thread."""

        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name=f"TelegramTypingPulse:{self.chat_id}",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop the typing pulse thread."""

        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None

    def _run(self) -> None:
        """Run the periodic typing action loop."""

        while not self._stop_event.is_set():
            try:
                _telegram_send_chat_action(self.token, self.chat_id, action="typing")
            except Exception:
                pass
            if self._stop_event.wait(self.interval):
                break


class _TelegramPhaseReporter:
    """Progress reporter for long Telegram chat turns."""

    def __init__(
        self,
        token: str,
        chat_id: int,
        reply_to_message_id: Optional[int] = None,
        idle_notice_delay: float = 60.0,
        heartbeat_interval: float = 60.0,
    ) -> None:
        """Initialize the progress reporter."""

        self.token = token
        self.chat_id = chat_id
        self.reply_to_message_id = reply_to_message_id
        self.idle_notice_delay = idle_notice_delay
        self.heartbeat_interval = heartbeat_interval
        self.preface_text = ""
        self.preface_sent = False
        self._idle_notice_sent = False
        self._last_tool_notice = ""
        self._last_tool_notice_ts = 0.0
        self._current_stage = "分析需求"
        self._last_progress_ts = time.time()
        self._stop_event = threading.Event()
        self._progress_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the progress heartbeat thread."""

        if self._progress_thread and self._progress_thread.is_alive():
            return
        self._stop_event.clear()
        self._progress_thread = threading.Thread(
            target=self._progress_loop,
            name=f"TelegramProgress:{self.chat_id}",
            daemon=True,
        )
        self._progress_thread.start()

    def stop(self) -> None:
        """Stop the progress heartbeat thread."""

        self._stop_event.set()
        if self._progress_thread and self._progress_thread.is_alive():
            self._progress_thread.join(timeout=0.5)
        self._progress_thread = None

    def capture_preface(self, text: str) -> None:
        """Store a preface preview emitted before tool execution."""

        cleaned = (text or "").strip()
        if cleaned:
            self.preface_text = cleaned

    def send_preface_if_needed(self) -> None:
        """Send the captured preface to Telegram once."""

        if self.preface_sent or not self.preface_text:
            return
        try:
            _telegram_send_text(
                self.token,
                self.chat_id,
                self.preface_text,
                reply_to_message_id=self.reply_to_message_id,
            )
            self.preface_sent = True
            self._note_progress("前置说明")
            telegram_log(f"telegram preface chat={self.chat_id} len={len(self.preface_text)}")
        except Exception:
            pass

    def tool_start(self, name: str) -> None:
        """Report the start of a tool call to Telegram."""

        self.send_preface_if_needed()
        tool_name = (name or "").strip() or "unknown"
        now = time.time()
        if tool_name == self._last_tool_notice and now - self._last_tool_notice_ts < 1.5:
            return
        self._last_tool_notice = tool_name
        self._last_tool_notice_ts = now
        self._current_stage = f"执行工具 {tool_name}"
        try:
            _telegram_send_text(
                self.token,
                self.chat_id,
                f"🔧 正在调用工具: {tool_name}",
                reply_to_message_id=self.reply_to_message_id,
            )
            self._note_progress(self._current_stage)
            telegram_log(f"telegram tool_start chat={self.chat_id} name={tool_name}")
        except Exception:
            pass

    def tool_finish(self, name: str, preview: str = "") -> None:
        """Report a successful tool call to Telegram."""

        tool_name = (name or "").strip() or "unknown"
        self._current_stage = f"等待下一步 ({tool_name} 已完成)"
        text = f"✅ 工具完成: {tool_name}"
        snippet = (preview or "").strip()
        if snippet:
            snippet = snippet[:100]
            text += f"\n{snippet}"
        try:
            _telegram_send_text(
                self.token,
                self.chat_id,
                text,
                reply_to_message_id=self.reply_to_message_id,
            )
            self._note_progress(self._current_stage)
            telegram_log(f"telegram tool_finish chat={self.chat_id} name={tool_name}")
        except Exception:
            pass

    def tool_error(self, name: str, error: str) -> None:
        """Report a failed tool call to Telegram."""

        self.send_preface_if_needed()
        self._current_stage = f"工具失败 {(name or '').strip() or 'unknown'}"
        try:
            detail = (error or "").strip()
            if len(detail) > 160:
                detail = detail[:157] + "..."
            _telegram_send_text(
                self.token,
                self.chat_id,
                f"❌ 工具失败: {(name or '').strip() or 'unknown'}\n{detail or '未知错误'}",
                reply_to_message_id=self.reply_to_message_id,
            )
            self._note_progress(self._current_stage)
            telegram_log(
                f"telegram tool_error chat={self.chat_id} name={(name or '').strip() or 'unknown'} detail={detail[:80]}"
            )
        except Exception:
            pass

    def strip_preface_from_reply(self, reply: str) -> str:
        """Remove the already-sent preface from the final reply body."""

        cleaned_reply = (reply or "").strip()
        preface = self.preface_text.strip()
        if not self.preface_sent or not preface or not cleaned_reply:
            return cleaned_reply
        if cleaned_reply == preface:
            return ""
        prefix = preface + "\n\n"
        if cleaned_reply.startswith(prefix):
            return cleaned_reply[len(prefix) :].lstrip()
        return cleaned_reply

    def _note_progress(self, stage: str) -> None:
        """Update the last-progress timestamp."""

        self._current_stage = stage
        self._last_progress_ts = time.time()

    def _progress_loop(self) -> None:
        """Send idle and heartbeat progress notices."""

        while not self._stop_event.wait(1.0):
            now = time.time()
            if (
                not self._idle_notice_sent
                and not self.preface_sent
                and not self._last_tool_notice
                and now - self._last_progress_ts >= self.idle_notice_delay
            ):
                try:
                    _telegram_send_text(
                        self.token,
                        self.chat_id,
                        "Gary 正在分析需求，准备开始处理。",
                        reply_to_message_id=self.reply_to_message_id,
                    )
                    self._idle_notice_sent = True
                    self._note_progress("分析需求")
                    telegram_log(f"telegram idle_notice chat={self.chat_id}")
                except Exception:
                    pass
                continue

            if now - self._last_progress_ts < self.heartbeat_interval:
                continue

            stage = self._current_stage or "处理中"
            try:
                _telegram_send_text(
                    self.token,
                    self.chat_id,
                    f"⏳ Gary 仍在处理: {stage}",
                    reply_to_message_id=self.reply_to_message_id,
                )
                self._note_progress(stage)
                telegram_log(f"telegram heartbeat chat={self.chat_id} stage={stage}")
            except Exception:
                pass


def _telegram_is_authorized(config: dict[str, Any], chat_id: int, user_id: int) -> bool:
    """Return whether the chat or user is authorized to use the bot."""

    if config.get("allow_all_chats"):
        return True
    if chat_id in set(config.get("allowed_chat_ids", [])):
        return True
    if user_id in set(config.get("allowed_user_ids", [])):
        return True
    return False


def _telegram_unauthorized_text(chat_id: int, user_id: int) -> str:
    """Return the standard unauthorized reply text."""

    return (
        "这个 Telegram 会话还没授权。\n\n"
        f"chat_id = {chat_id}\n"
        f"user_id = {user_id}\n\n"
        "请在终端执行任一命令后再试：\n"
        f"gary telegram allow {chat_id}\n"
        f"gary telegram allow user:{user_id}"
    )


def telegram_status_lines(include_commands: bool = True) -> list[str]:
    """Build the CLI status lines for Telegram configuration."""

    config = _read_telegram_config()
    daemon = _telegram_daemon_status()
    lines = [
        "Telegram 机器人状态",
        f"AI 接口: {'已配置' if _is_ai_configured() else '未配置'}",
        f"机器人: {'已配置' if telegram_is_configured(config) else '未配置'}",
        f"Token: {_mask_telegram_token(config.get('bot_token', ''))}",
        f"Bot: @{config.get('bot_username') or '-'}",
        f"Bot 名称: {config.get('bot_name') or '-'}",
        f"授权模式: {'允许所有 chat' if config.get('allow_all_chats') else '白名单'}",
        f"允许的 chat_id: {config.get('allowed_chat_ids') or '[]'}",
        f"允许的 user_id: {config.get('allowed_user_ids') or '[]'}",
        f"守护进程: {'运行中' if daemon['running'] else '未运行'}",
        f"PID: {daemon.get('pid') or '-'}",
        f"日志: {daemon['log_path']}",
        f"last_update_id: {config.get('last_update_id', 0)}",
    ]
    if include_commands:
        lines.extend(
            [
                "",
                "常用命令:",
                "gary telegram start        启动后台机器人",
                "gary telegram stop         停止后台机器人",
                "gary telegram allow <id>   添加 chat_id 白名单",
                "gary telegram allow user:<id>   添加 user_id 白名单",
                "gary telegram remove <id>  删除白名单",
                "gary telegram allow-all    允许所有 chat",
                "gary telegram whitelist    切回白名单模式",
                "gary telegram reset        删除 Telegram 配置并停止机器人",
            ]
        )
    return lines


def _print_telegram_status(include_commands: bool = True) -> None:
    """Render Telegram status in the configured console."""

    _console().print("\n".join(telegram_status_lines(include_commands=include_commands)))
    _console().print()


def _telegram_help_text() -> str:
    """Return the Telegram-side help text."""

    return "\n".join(
        [
            "Telegram 侧可用命令：",
            "/start  查看状态和授权信息",
            "/help   查看帮助",
            "/clear  清空当前聊天上下文",
            "/status 查看 Gary 当前硬件状态",
            "/connect [芯片] 连接探针和串口",
            "/disconnect 断开硬件",
            "/chip [型号] 查看或切换芯片",
            "/projects 查看最近历史项目",
            "",
            "其他普通文本会直接发给 Gary，保持当前聊天上下文连续对话。",
        ]
    )


def _format_hw_status_for_text(status: dict[str, Any]) -> str:
    """Format the hardware status for a plain text Telegram reply."""

    return "\n".join(
        [
            "Gary 当前状态",
            f"chip: {status.get('chip', '-')}",
            f"hw_connected: {status.get('hw_connected', False)}",
            f"serial_connected: {status.get('serial_connected', False)}",
            f"gcc_ok: {status.get('gcc_ok', False)}",
            f"gcc_version: {status.get('gcc_version', '-')}",
            f"hal_ok: {status.get('hal_ok', False)}",
            f"hal_lib_ok: {status.get('hal_lib_ok', False)}",
            f"workspace: {status.get('workspace', '-')}",
        ]
    )


def _format_projects_for_text(projects: list[dict[str, Any]]) -> str:
    """Format recent projects for a plain text Telegram reply."""

    if not projects:
        return "暂无历史项目"
    lines = ["最近项目："]
    for item in projects[:10]:
        lines.append(
            f"- {item.get('name', '-')}"
            f" | {item.get('chip', '-')}"
            f" | {str(item.get('request', ''))[:40]}"
        )
    return "\n".join(lines)


def _normalize_telegram_incoming_text(text: str, bot_username: str) -> Optional[str]:
    """Strip bot mentions from incoming commands and validate the target bot."""

    stripped = (text or "").strip()
    if not stripped.startswith("/"):
        return stripped
    head, sep, tail = stripped.partition(" ")
    command = head
    if "@" in head:
        base, mention = head.split("@", 1)
        if bot_username and mention.lower() != bot_username.lower():
            return None
        command = base
    return f"{command}{sep}{tail}".strip()


def configure_telegram_cli() -> dict[str, Any]:
    """Run the interactive Telegram configuration wizard."""

    _console().print()
    _console().rule("[bold cyan]  配置 Telegram 机器人[/]")
    _console().print()

    config = _read_telegram_config()
    if telegram_is_configured(config):
        _console().print(
            f"  [dim]当前 Token:[/] {_mask_telegram_token(config.get('bot_token', ''))}"
        )
        _console().print(f"  [dim]当前 Bot  :[/] @{config.get('bot_username') or '-'}")
        _console().print(
            f"  [dim]授权模式 :[/] {'允许所有 chat' if config.get('allow_all_chats') else '白名单'}"
        )
        _console().print(f"  [dim]chat_id   :[/] {config.get('allowed_chat_ids') or '[]'}")
        _console().print(f"  [dim]user_id   :[/] {config.get('allowed_user_ids') or '[]'}")
        _console().print()

    current_token = str(config.get("bot_token", "")).strip()
    while True:
        try:
            prompt = "  Bot Token"
            if current_token:
                prompt += "（回车保留当前）"
            prompt += ": "
            entered = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            _console().print("\n[dim]已取消[/]")
            return {"success": False, "message": "已取消"}

        token = entered or current_token
        if not token:
            _console().print("[yellow]  Bot Token 不能为空[/]")
            continue
        try:
            me = _telegram_get_me(token)
            config["bot_token"] = token
            config["bot_id"] = me.get("id")
            config["bot_username"] = me.get("username", "")
            config["bot_name"] = me.get("first_name", "")
            _console().print(f"[green]  ✓ Token 有效，机器人: @{config['bot_username']}[/]")
            break
        except Exception as exc:
            _console().print(f"[red]  ✗ Token 校验失败: {exc}[/]")

    _console().print()
    _console().print("[bold cyan]  授权模式[/]")
    _console().print("    [yellow]1[/]. 白名单（推荐）")
    _console().print("    [yellow]2[/]. 允许所有 chat")
    _console().print()

    default_choice = "2" if config.get("allow_all_chats") else "1"
    try:
        choice = input(f"  输入序号 [1-2]（默认 {default_choice}）: ").strip() or default_choice
    except (EOFError, KeyboardInterrupt):
        choice = default_choice

    config["allow_all_chats"] = choice == "2"

    if not config["allow_all_chats"]:
        try:
            raw_targets = input(
                "  输入白名单（chat_id 或 user:123，多项用空格/逗号分隔，回车保留当前）: "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            raw_targets = ""
        if raw_targets:
            parsed = _parse_telegram_targets(raw_targets)
            if parsed["invalid"]:
                _console().print(f"[yellow]  忽略非法项: {parsed['invalid']}[/]")
            config["allowed_chat_ids"] = parsed["chat_ids"]
            config["allowed_user_ids"] = parsed["user_ids"]

    saved = _write_telegram_config(config)
    try:
        _telegram_set_my_commands(saved["bot_token"])
    except Exception as exc:
        _console().print(f"[yellow]  命令菜单注册失败，可忽略: {exc}[/]")

    _console().print()
    _console().print("[green]  ✓ Telegram 配置已保存[/]")
    _console().print(f"  [green]✓[/] Bot       @{saved.get('bot_username') or '-'}")
    _console().print(
        f"  [green]✓[/] Token     {_mask_telegram_token(saved.get('bot_token', ''))}"
    )
    _console().print(
        f"  [green]✓[/] 授权模式  {'允许所有 chat' if saved.get('allow_all_chats') else '白名单'}"
    )
    if not saved.get("allow_all_chats"):
        _console().print(f"  [green]✓[/] chat_id   {saved.get('allowed_chat_ids') or '[]'}")
        _console().print(f"  [green]✓[/] user_id   {saved.get('allowed_user_ids') or '[]'}")
        _console().print(
            "  [dim]若还不知道 chat_id，可先在 Telegram 给机器人发 /start，再按提示执行 allow 命令[/]"
        )
    _console().print()
    return {"success": True, "config": saved}


def _ensure_ai_for_telegram() -> bool:
    """Ensure AI configuration exists before enabling Telegram."""

    if _is_ai_configured():
        return True
    _console().print("[yellow]Telegram 机器人要能回复，需要先配置 AI 接口[/]")
    if _HOOKS.configure_ai_cli is None:
        raise RuntimeError(
            "Telegram integration is not configured: configure_ai_cli is missing"
        )
    _HOOKS.configure_ai_cli()
    if _is_ai_configured():
        return True
    _console().print("[red]AI 接口仍未配置，无法启动 Telegram 机器人[/]")
    return False


def start_telegram_bot() -> dict[str, Any]:
    """Start the Telegram daemon process when needed."""

    daemon = _telegram_daemon_status()
    if daemon["running"]:
        return {"success": True, "message": f"Telegram 机器人已在后台运行（PID {daemon['pid']}）"}

    config = _read_telegram_config()
    if not telegram_is_configured(config):
        return {
            "success": False,
            "message": "Telegram 机器人尚未配置，请先运行 gary telegram 或 /telegram",
        }
    if not _is_ai_configured():
        return {"success": False, "message": "AI 接口未配置，先运行 gary config 或 /config"}

    _ensure_gary_home()
    log_handle = TELEGRAM_LOG_PATH.open("a", encoding="utf-8")
    log_handle.write(
        f"\n[{datetime.now().isoformat(timespec='seconds')}] starting telegram daemon\n"
    )
    log_handle.flush()
    try:
        process = subprocess.Popen(
            [sys.executable, str(_script_path()), "telegram", "serve", "--daemonized"],
            cwd=str(_workdir()),
            stdout=log_handle,
            stderr=log_handle,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
    finally:
        log_handle.close()

    time.sleep(1.2)
    if _pid_is_alive(process.pid):
        return {
            "success": True,
            "message": f"Telegram 机器人已启动（PID {process.pid}）",
            "pid": process.pid,
        }
    return {"success": False, "message": f"后台启动失败，请查看日志: {TELEGRAM_LOG_PATH}"}


def stop_telegram_bot() -> dict[str, Any]:
    """Stop the Telegram daemon process when it is running."""

    daemon = _telegram_daemon_status()
    pid = daemon.get("pid")
    if not daemon["running"] or not pid:
        return {"success": True, "message": "Telegram 机器人当前未运行"}

    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as exc:
        _clear_pid_file(pid)
        return {"success": False, "message": f"停止失败: {exc}"}

    for _ in range(20):
        if not _pid_is_alive(pid):
            _clear_pid_file(pid)
            return {"success": True, "message": f"Telegram 机器人已停止（PID {pid}）"}
        time.sleep(0.2)

    return {"success": False, "message": f"停止超时，请手动检查 PID {pid}"}


def _reset_telegram_config() -> dict[str, Any]:
    """Stop the bot and delete the Telegram configuration file."""

    stop_telegram_bot()
    if TELEGRAM_CONFIG_PATH.exists():
        TELEGRAM_CONFIG_PATH.unlink()
    return {"success": True, "message": f"已删除 Telegram 配置: {TELEGRAM_CONFIG_PATH}"}


class TelegramBotBridge:
    """Long-polling bridge between Telegram and a per-chat Gary agent."""

    def __init__(self) -> None:
        """Initialize the bridge state."""

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._chat_agents: dict[int, TelegramAgent] = {}
        self._last_error = ""
        self._started_at: Optional[float] = None

    def is_running(self) -> bool:
        """Return whether the local bridge thread is alive."""

        return bool(self._thread and self._thread.is_alive())

    def start(self) -> dict[str, Any]:
        """Start the local Telegram bridge thread."""

        config = _read_telegram_config()
        if not telegram_is_configured(config):
            return {"success": False, "message": "Telegram 机器人未配置"}
        if not _is_ai_configured():
            return {"success": False, "message": "AI 接口未配置"}
        if self.is_running():
            return {"success": True, "message": "Telegram 机器人已在当前进程运行"}
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._poll_loop,
            name="GaryTelegramBridge",
            daemon=True,
        )
        self._thread.start()
        self._started_at = time.time()
        return {"success": True, "message": "Telegram 机器人已启动"}

    def stop(self) -> None:
        """Stop the local Telegram bridge thread."""

        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._thread = None

    def status(self) -> dict[str, Any]:
        """Return bridge runtime status."""

        return {
            "running": self.is_running(),
            "started_at": self._started_at,
            "last_error": self._last_error,
            "chat_sessions": len(self._chat_agents),
        }

    def _get_agent(self, chat_id: int) -> TelegramAgent:
        """Return the cached Gary agent for a Telegram chat."""

        agent = self._chat_agents.get(chat_id)
        if agent is None:
            agent = _agent_factory()(interactive=False)
            self._chat_agents[chat_id] = agent
        agent.refresh_ai_client()
        return agent

    def _reset_chat(self, chat_id: int) -> None:
        """Clear the cached Gary agent for a Telegram chat."""

        self._chat_agents.pop(chat_id, None)

    def _poll_loop(self) -> None:
        """Run the long-polling loop against the Telegram Bot API."""

        while not self._stop_event.is_set():
            config = _read_telegram_config()
            token = str(config.get("bot_token", "")).strip()
            if not token:
                self._last_error = "Telegram Token 为空"
                time.sleep(2.0)
                continue

            latest_seen = int(config.get("last_update_id", 0))
            try:
                updates = (
                    _telegram_api_call(
                        token,
                        "getUpdates",
                        {
                            "offset": latest_seen + 1,
                            "timeout": 25,
                            "allowed_updates": ["message"],
                        },
                        timeout=35.0,
                    )
                    or []
                )
                self._last_error = ""
            except Exception as exc:
                self._last_error = str(exc)
                time.sleep(2.0)
                continue

            for update in updates:
                latest_seen = max(latest_seen, int(update.get("update_id", 0)))
                try:
                    self._handle_update(update)
                except Exception as exc:
                    self._last_error = str(exc)
                    _console().print(f"[red]Telegram 处理失败: {exc}[/]")

            if latest_seen > int(config.get("last_update_id", 0)):
                config["last_update_id"] = latest_seen
                _write_telegram_config(config)

    def _handle_update(self, update: dict[str, Any]) -> None:
        """Handle a single Telegram update payload."""

        message = update.get("message")
        if not message:
            return

        chat = message.get("chat") or {}
        from_user = message.get("from") or {}
        text = message.get("text", "")
        if not text:
            return

        config = _read_telegram_config()
        token = config["bot_token"]
        chat_id = int(chat.get("id"))
        user_id = int(from_user.get("id", 0))
        message_id = message.get("message_id")
        normalized = _normalize_telegram_incoming_text(
            text,
            str(config.get("bot_username", "")),
        )
        if normalized is None:
            return
        update_id = int(update.get("update_id", 0))
        preview = normalized.replace("\n", " ").strip()[:80]
        telegram_log(
            f"telegram update={update_id} chat={chat_id} user={user_id} text={preview!r}"
        )

        if normalized.startswith("/"):
            if _telegram_is_authorized(config, chat_id, user_id):
                with _TelegramTypingPulse(token, chat_id):
                    handled, reply = self._handle_command(normalized, config, chat_id, user_id)
                    if handled:
                        if reply:
                            _telegram_send_text(
                                token,
                                chat_id,
                                reply,
                                reply_to_message_id=message_id,
                            )
                        return
            else:
                handled, reply = self._handle_command(normalized, config, chat_id, user_id)
                if handled:
                    if reply:
                        _telegram_send_text(
                            token,
                            chat_id,
                            reply,
                            reply_to_message_id=message_id,
                        )
                    return

        if not _telegram_is_authorized(config, chat_id, user_id):
            telegram_log(f"telegram unauthorized chat={chat_id} user={user_id}")
            _telegram_send_text(
                token,
                chat_id,
                _telegram_unauthorized_text(chat_id, user_id),
                reply_to_message_id=message_id,
            )
            return

        agent = self._get_agent(chat_id)
        reporter = _TelegramPhaseReporter(token, chat_id, reply_to_message_id=message_id)

        def _on_text(preview_text: str) -> None:
            reporter.capture_preface(preview_text)

        def _on_tool(event: dict[str, Any]) -> None:
            phase = event.get("phase")
            name = str(event.get("name", ""))
            if phase == "start":
                reporter.tool_start(name)
            elif phase == "finish":
                reporter.tool_finish(name, str(event.get("preview", "")))
            elif phase == "error":
                reporter.tool_error(name, str(event.get("error", "")))

        with _TelegramTypingPulse(token, chat_id):
            reporter.start()
            started_at = time.time()
            try:
                reply = agent.chat(
                    normalized,
                    stream_to_console=False,
                    text_callback=_on_text,
                    tool_callback=_on_tool,
                ).strip()
            finally:
                reporter.stop()
            reply = reporter.strip_preface_from_reply(reply)
            if not reply:
                telegram_log(
                    f"telegram empty_final chat={chat_id} preface_sent={reporter.preface_sent} preface_len={len(reporter.preface_text)}"
                )
                reply = "工具已执行，但 AI 没有返回最终正文。请重试一次；若仍复现，我会继续排查。"
            _telegram_send_text(token, chat_id, reply, reply_to_message_id=message_id)
            telegram_log(
                f"telegram reply chat={chat_id} elapsed={time.time() - started_at:.1f}s len={len(reply)}"
            )

    def _handle_command(
        self,
        command_text: str,
        config: dict[str, Any],
        chat_id: int,
        user_id: int,
    ) -> tuple[bool, str]:
        """Handle Telegram slash commands inside a chat."""

        parts = command_text.split(None, 1)
        head = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""
        authorized = _telegram_is_authorized(config, chat_id, user_id)

        if head in ("/start", "/help"):
            if authorized:
                return True, _telegram_help_text()
            return True, _telegram_unauthorized_text(chat_id, user_id) + "\n\n发送授权后再试。"

        if not authorized:
            return True, _telegram_unauthorized_text(chat_id, user_id)

        if head in ("/clear", "/new"):
            self._reset_chat(chat_id)
            return True, "当前 Telegram 会话上下文已清空。"

        if head == "/status":
            return True, _format_hw_status_for_text(_hardware_status())

        if head == "/connect":
            result = _connect(arg or None)
            return True, result.get("message", json.dumps(result, ensure_ascii=False))

        if head == "/disconnect":
            result = _disconnect()
            return True, result.get("message", json.dumps(result, ensure_ascii=False))

        if head == "/chip":
            if not arg:
                return True, f"当前芯片: {_current_chip() or '(未设置)'}"
            result = _set_chip(arg)
            return True, f"已切换芯片: {result.get('chip')} ({result.get('family')})"

        if head == "/projects":
            result = _list_projects()
            return True, _format_projects_for_text(result.get("projects", []))

        if head == "/serial":
            tokens = arg.split()
            if tokens and tokens[0] == "list":
                ports = _detect_serial_ports()
                return True, "可用串口: " + (", ".join(ports) if ports else "无")
            port = tokens[0] if tokens and tokens[0].startswith("/dev/") else None
            baud = None
            for token in tokens:
                if token.isdigit():
                    baud = int(token)
                    break
            result = _serial_connect(port, baud)
            return True, result.get("message", json.dumps(result, ensure_ascii=False))

        if head == "/telegram":
            return True, "\n".join(telegram_status_lines(include_commands=False))

        return False, ""


_telegram_bridge = TelegramBotBridge()


def stop_local_telegram_bridge() -> None:
    """Stop the in-process Telegram bridge thread."""

    _telegram_bridge.stop()


def serve_telegram_forever(daemonized: bool = False) -> int:
    """Run the in-process Telegram bot loop until interrupted."""

    if not telegram_is_configured():
        _console().print("[red]Telegram 机器人未配置[/]")
        return 1
    if not _is_ai_configured():
        _console().print("[red]AI 接口未配置，无法启动 Telegram 机器人[/]")
        return 1

    result = _telegram_bridge.start()
    if not result["success"]:
        _console().print(f"[red]{result['message']}[/]")
        return 1

    if daemonized:
        _write_pid_file(os.getpid())
        atexit.register(lambda: _clear_pid_file(os.getpid()))

    _console().print("[green]Telegram 机器人正在运行，Ctrl+C 停止[/]")
    try:
        while _telegram_bridge.is_running():
            time.sleep(1.0)
    except KeyboardInterrupt:
        _console().print("\n[yellow]收到停止信号，正在退出 Telegram 机器人...[/]")
    finally:
        _telegram_bridge.stop()
        if daemonized:
            _clear_pid_file(os.getpid())
    return 0


def _interactive_telegram_menu() -> bool:
    """Show the interactive Telegram management menu."""

    _console().print()
    _console().rule("[bold cyan]  Telegram 管理[/]")
    _console().print()
    _print_telegram_status(include_commands=False)
    _console().print("[bold cyan]  可执行操作：[/]")
    _console().print("    [yellow]1[/]. 查看状态")
    _console().print("    [yellow]2[/]. 重新配置机器人")
    _console().print("    [yellow]3[/]. 启动后台机器人")
    _console().print("    [yellow]4[/]. 停止后台机器人")
    _console().print("    [yellow]5[/]. 添加白名单")
    _console().print("    [yellow]6[/]. 删除白名单")
    _console().print("    [yellow]7[/]. 允许所有 chat")
    _console().print("    [yellow]8[/]. 切回白名单模式")
    _console().print("    [yellow]9[/]. 重置 Telegram 配置")
    _console().print()

    try:
        choice = input("  输入序号（回车取消）: ").strip()
    except (EOFError, KeyboardInterrupt):
        _console().print("\n[dim]已取消[/]\n")
        return True

    if not choice:
        _console().print("[dim]已取消[/]\n")
        return True

    if choice == "1":
        _print_telegram_status(include_commands=True)
        return True

    if choice == "2":
        if not _ensure_ai_for_telegram():
            return True
        result = configure_telegram_cli()
        if result.get("success"):
            daemon = _telegram_daemon_status()
            if daemon["running"]:
                stop_result = stop_telegram_bot()
                start_result = start_telegram_bot()
                _console().print(
                    f"[{'green' if stop_result['success'] else 'red'}]{stop_result['message']}[/]"
                )
                _console().print(
                    f"[{'green' if start_result['success'] else 'red'}]{start_result['message']}[/]"
                )
                _console().print()
        return True

    if choice == "3":
        return handle_telegram_command("start", source="builtin")

    if choice == "4":
        return handle_telegram_command("stop", source="builtin")

    if choice in ("5", "6"):
        action = "allow" if choice == "5" else "remove"
        label = "添加" if choice == "5" else "删除"
        try:
            raw = input(f"  输入要{label}的 chat_id 或 user:123（可多个，空格分隔）: ").strip()
        except (EOFError, KeyboardInterrupt):
            _console().print("\n[dim]已取消[/]\n")
            return True
        if not raw:
            _console().print("[dim]已取消[/]\n")
            return True
        return handle_telegram_command(f"{action} {raw}", source="builtin")

    if choice == "7":
        return handle_telegram_command("allow-all", source="builtin")

    if choice == "8":
        return handle_telegram_command("whitelist", source="builtin")

    if choice == "9":
        try:
            confirm = input("  确认重置并删除 Telegram 配置？输入 yes 确认: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            _console().print("\n[dim]已取消[/]\n")
            return True
        if confirm != "yes":
            _console().print("[dim]已取消[/]\n")
            return True
        return handle_telegram_command("reset", source="builtin")

    _console().print(f"[yellow]未知选项: {choice}[/]\n")
    return True


def handle_telegram_command(args: str, source: str = "cli") -> bool:
    """Handle the `gary telegram ...` command family."""

    arg = (args or "").strip()
    config = _read_telegram_config()
    parts = arg.split(None, 1)
    subcmd = parts[0].lower() if parts and parts[0] else ""
    subarg = parts[1].strip() if len(parts) > 1 else ""

    if subcmd == "":
        if source == "builtin":
            return _interactive_telegram_menu()
        if not telegram_is_configured(config):
            _console().print("[yellow]Telegram 机器人尚未配置，进入配置向导[/]")
            if not _ensure_ai_for_telegram():
                return True
            result = configure_telegram_cli()
            if not result.get("success"):
                return True
            start_result = start_telegram_bot()
            _console().print(
                f"[{'green' if start_result['success'] else 'red'}]{start_result['message']}[/]"
            )
            _console().print()
            return True
        _print_telegram_status(include_commands=True)
        return True

    if subcmd in ("status", "info", "list", "ls"):
        _print_telegram_status(include_commands=True)
        return True

    if subcmd in ("config", "setup"):
        if not _ensure_ai_for_telegram():
            return True
        configure_telegram_cli()
        return True

    if subcmd in ("start", "run"):
        if not telegram_is_configured(config):
            _console().print("[yellow]Telegram 机器人尚未配置，进入配置向导[/]")
            if not _ensure_ai_for_telegram():
                return True
            result = configure_telegram_cli()
            if not result.get("success"):
                return True
        elif not _ensure_ai_for_telegram():
            return True
        result = start_telegram_bot()
        _console().print(f"[{'green' if result['success'] else 'red'}]{result['message']}[/]")
        _console().print()
        return True

    if subcmd == "serve":
        daemonized = "--daemonized" in _split_tokens(subarg)
        sys.exit(serve_telegram_forever(daemonized=daemonized))

    if subcmd == "stop":
        result = stop_telegram_bot()
        _console().print(f"[{'green' if result['success'] else 'red'}]{result['message']}[/]")
        _console().print()
        return True

    if subcmd == "restart":
        stop_result = stop_telegram_bot()
        start_result = start_telegram_bot()
        _console().print(
            f"[{'green' if stop_result['success'] else 'red'}]{stop_result['message']}[/]"
        )
        _console().print(
            f"[{'green' if start_result['success'] else 'red'}]{start_result['message']}[/]"
        )
        _console().print()
        return True

    if subcmd in ("allow", "add"):
        if not subarg:
            _console().print("[yellow]用法: gary telegram allow <chat_id|user:123> [...][/]\n")
            return True
        parsed = _parse_telegram_targets(subarg)
        if parsed["invalid"]:
            _console().print(f"[yellow]忽略非法项: {parsed['invalid']}[/]")
        saved = _telegram_set_permissions(
            add_chat_ids=parsed["chat_ids"],
            add_user_ids=parsed["user_ids"],
        )
        _console().print("[green]Telegram 白名单已更新[/]")
        _console().print(f"  chat_id: {saved['allowed_chat_ids']}")
        _console().print(f"  user_id: {saved['allowed_user_ids']}\n")
        return True

    if subcmd in ("remove", "delete", "del", "rm"):
        if not subarg:
            _console().print("[yellow]用法: gary telegram remove <chat_id|user:123> [...][/]\n")
            return True
        parsed = _parse_telegram_targets(subarg)
        if parsed["invalid"]:
            _console().print(f"[yellow]忽略非法项: {parsed['invalid']}[/]")
        saved = _telegram_set_permissions(
            remove_chat_ids=parsed["chat_ids"],
            remove_user_ids=parsed["user_ids"],
        )
        _console().print("[green]Telegram 白名单已更新[/]")
        _console().print(f"  chat_id: {saved['allowed_chat_ids']}")
        _console().print(f"  user_id: {saved['allowed_user_ids']}\n")
        return True

    if subcmd == "allow-all":
        saved = _telegram_set_permissions(allow_all_chats=True)
        _console().print("[green]已切换为允许所有 chat[/]")
        _console().print(f"  chat_id: {saved['allowed_chat_ids']}")
        _console().print(f"  user_id: {saved['allowed_user_ids']}\n")
        return True

    if subcmd == "whitelist":
        saved = _telegram_set_permissions(allow_all_chats=False)
        _console().print("[green]已切换为白名单模式[/]")
        _console().print(f"  chat_id: {saved['allowed_chat_ids']}")
        _console().print(f"  user_id: {saved['allowed_user_ids']}\n")
        return True

    if subcmd == "reset":
        result = _reset_telegram_config()
        _console().print(f"[{'green' if result['success'] else 'red'}]{result['message']}[/]")
        _console().print()
        return True

    _console().print(f"[yellow]未知 Telegram 命令: {subcmd}[/]")
    _print_telegram_status(include_commands=True)
    return True


__all__ = [
    "TELEGRAM_CONFIG_PATH",
    "TELEGRAM_LOG_PATH",
    "TELEGRAM_MESSAGE_LIMIT",
    "TELEGRAM_PID_PATH",
    "configure_telegram_cli",
    "configure_telegram_integration",
    "get_telegram_target_candidates",
    "handle_telegram_command",
    "serve_telegram_forever",
    "start_telegram_bot",
    "stop_local_telegram_bridge",
    "stop_telegram_bot",
    "telegram_is_configured",
    "telegram_log",
    "telegram_status_lines",
]
