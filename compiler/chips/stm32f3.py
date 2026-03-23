"""STM32F3 compiler implementation."""

from __future__ import annotations

from pathlib import Path

from ..base import ChipCompiler, CompileResult
from ..registry import register


@register
class STM32F3Compiler(ChipCompiler):
    """Compiler for the STM32F3 family."""

    SUPPORTED_PREFIXES = ["STM32F3"]
    FAMILY = "f3"

    def compile(self, source_path: str | Path, chip: str) -> CompileResult:
        """Compile a bare-metal source file for STM32F3 chips."""
        return self._compile_baremetal(source_path, chip)

    def get_flash_command(self, bin_path: str | Path, chip: str) -> list[str]:
        """Return the pyOCD flash command for the selected STM32F3 chip."""
        return self._build_flash_command(bin_path, chip)

