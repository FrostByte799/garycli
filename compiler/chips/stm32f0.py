"""STM32F0 compiler implementation."""

from __future__ import annotations

from pathlib import Path

from ..base import ChipCompiler, CompileResult
from ..registry import register


@register
class STM32F0Compiler(ChipCompiler):
    """Compiler for the STM32F0 family."""

    SUPPORTED_PREFIXES = ["STM32F0"]
    FAMILY = "f0"

    def compile(self, source_path: str | Path, chip: str) -> CompileResult:
        """Compile a bare-metal source file for STM32F0 chips."""
        return self._compile_baremetal(source_path, chip)

    def get_flash_command(self, bin_path: str | Path, chip: str) -> list[str]:
        """Return the pyOCD flash command for the selected STM32F0 chip."""
        return self._build_flash_command(bin_path, chip)
