"""Specialized debug prompt fragments."""

from __future__ import annotations

from pathlib import Path
from typing import Any

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

_COMPILE_ERROR_PROMPT = """## 编译失败专项诊断
- 优先读取编译错误首条和未定义符号，直接修复，不做泛泛分析。
- `undefined reference to _sbrk/end`：优先排查 `sprintf/printf/malloc`。
- `undefined reference to HAL_xxx`：优先检查 HAL 源文件、头文件和系列宏。
- `No such file` / `cannot find`：优先检查 include 路径、生成文件和工具链依赖。
- 若是增量修改造成的错误，优先 `str_replace_edit` + `stm32_recompile`，不要整文件重写。"""

_I2C_FAILURE_PROMPT = """## I2C 失败专项诊断
- 优先看 `SR1.AF`、`SR1.ARLO`、`SR2.BUSY`，先判断是设备未接、地址错误还是总线锁死。
- 先确认 `HAL_I2C_IsDeviceReady()` 是否存在，传感器地址是否使用 7-bit 左移规则。
- 若串口无 `Gary:BOOT`，怀疑初始化顺序不对，UART 打印必须早于 I2C/OLED/传感器初始化。
- 若外设未接，直接说明是硬件问题，停止继续修改业务逻辑。"""


def _load_template(name: str) -> str:
    """Load a markdown debug template from disk."""

    return (_TEMPLATES_DIR / name).read_text(encoding="utf-8").strip()


def _render_context(context: dict[str, Any]) -> str:
    """Render extra debug context into a compact markdown block."""

    if not context:
        return ""
    lines = ["", "### 当前上下文"]
    for key, value in context.items():
        snippet = str(value).strip()
        if not snippet:
            continue
        if len(snippet) > 240:
            snippet = snippet[:237] + "..."
        lines.append(f"- {key}: {snippet}")
    return "\n".join(lines) if len(lines) > 2 else ""


def get_debug_prompt(error_type: str, context: dict[str, Any]) -> str:
    """Return a specialized debug prompt fragment for the requested error type."""

    normalized = (error_type or "").strip().lower()
    if normalized in {"hardfault", "fault", "crash"}:
        prompt = _load_template("debug_hardfault.md")
    elif normalized in {"i2c", "i2c_failure", "sensor_i2c"}:
        prompt = _I2C_FAILURE_PROMPT
    elif normalized in {"compile", "compile_error", "build_error"}:
        prompt = _COMPILE_ERROR_PROMPT
    else:
        prompt = "## 通用诊断\n- 优先基于工具返回值和最新寄存器/串口结果做最小修改。"
    return prompt + _render_context(context)

