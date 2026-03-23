"""Modular STM32 compiler package with a legacy-compatible Compiler facade."""

from __future__ import annotations

import glob
import importlib
import sys
from pathlib import Path
from typing import Any

from . import base as _base_module
from . import registry as _registry_module

_PACKAGE_DIR = Path(__file__).resolve().parent
_CHIPS_DIR = _PACKAGE_DIR / "chips"


def _iter_chip_modules() -> list[str]:
    """Return all chip implementation module names under `compiler/chips`."""
    modules: list[str] = []
    for path_str in sorted(glob.glob(str(_CHIPS_DIR / "*.py"))):
        path = Path(path_str)
        if path.name == "__init__.py":
            continue
        modules.append(path.stem)
    return modules


def _autoload_chips(reload_existing: bool = False) -> None:
    """Import or reload every module under `compiler/chips`."""
    for module_name in _iter_chip_modules():
        full_name = f"{__name__}.chips.{module_name}"
        if reload_existing and full_name in sys.modules:
            importlib.reload(sys.modules[full_name])
        else:
            importlib.import_module(full_name)


def reload_package() -> None:
    """Reload base, registry, and all chip modules for hot-reload compatibility."""
    global _base_module, _registry_module
    importlib.invalidate_caches()
    _base_module = importlib.reload(_base_module)
    _registry_module = importlib.reload(_registry_module)
    _autoload_chips(reload_existing=True)
    _refresh_exports()


def get_package_mtime() -> float:
    """Return the latest modification time across the compiler package files."""
    latest = 0.0
    for path in _PACKAGE_DIR.rglob("*.py"):
        try:
            latest = max(latest, path.stat().st_mtime)
        except OSError:
            continue
    return latest


def _refresh_exports() -> None:
    """Refresh package-level re-exports after a hot reload."""
    globals()["CompileResult"] = _base_module.CompileResult
    globals()["ChipCompiler"] = _base_module.ChipCompiler
    globals()["CHIP_DB"] = _base_module.CHIP_DB
    globals()["lookup_chip"] = _base_module.lookup_chip
    globals()["get_compiler"] = _registry_module.get_compiler
    globals()["register"] = _registry_module.register


def _normalize_chip(chip_name: str | None) -> str:
    """Normalize a chip name while preserving the legacy default fallback."""
    return (
        _base_module.normalize_chip_name(chip_name)
        or _base_module.normalize_chip_name(_base_module.DEFAULT_CHIP)
        or "STM32F103C8"
    )


def _result_to_dict(result: _base_module.CompileResult) -> dict[str, Any]:
    """Convert the new dataclass result into the legacy dictionary payload."""
    return {
        "ok": result.success,
        "msg": result.error_output,
        "bin_path": result.bin_path,
        "bin_size": result.bin_size,
    }


class Compiler:
    """Legacy-compatible compiler facade used by `stm32_agent.py`."""

    def __init__(self) -> None:
        """Initialize facade state and mirror the historic public attributes."""
        self.has_gcc = False
        self.has_specs = False
        self.has_hal = False
        self.has_hal_lib = False
        self.hal_inc_dirs: list[str] = []
        self.hal_src_files: list[str] = []
        self._chip_info: dict[str, Any] | None = None
        self._current_family: str | None = None
        self._chip_name = _normalize_chip(_base_module.DEFAULT_CHIP)
        self._impl: _base_module.ChipCompiler | None = None

    def _sync_public_state(self) -> None:
        """Mirror internal implementation state for compatibility callers."""
        if self._impl is None:
            return
        self.has_gcc = self._impl.has_gcc
        self.has_specs = self._impl.has_specs
        self.has_hal = self._impl.has_hal
        self.has_hal_lib = self._impl.has_hal_lib
        self.hal_inc_dirs = list(self._impl.hal_inc_dirs)
        self.hal_src_files = list(self._impl.hal_src_files)
        self._chip_info = dict(self._impl._chip_info) if self._impl._chip_info else None
        self._current_family = self._impl._current_family

    def _ensure_impl(self, chip_name: str | None = None) -> _base_module.ChipCompiler:
        """Resolve and cache the family compiler for the selected chip."""
        normalized = _normalize_chip(chip_name or self._chip_name)
        try:
            if self._impl is None or not self._impl.supports(normalized):
                self._impl = get_compiler(normalized)
        except ValueError:
            fallback = _normalize_chip(_base_module.DEFAULT_CHIP)
            self._impl = get_compiler(fallback)
            normalized = _normalize_chip(normalized)
        self._chip_name = normalized
        return self._impl

    def set_chip(self, chip_name: str) -> dict[str, Any]:
        """Set the active chip and regenerate BSP helper files."""
        impl = self._ensure_impl(chip_name)
        chip_info = impl.set_chip(chip_name)
        self._sync_public_state()
        return chip_info

    def check(self, chip_name: str | None = None) -> dict[str, Any]:
        """Probe the toolchain and HAL environment for the selected chip."""
        impl = self._ensure_impl(chip_name)
        result = impl.check(chip_name or self._chip_name)
        self._sync_public_state()
        return result

    def precompile_hal(self) -> bool:
        """Precompile HAL sources for the active family."""
        impl = self._ensure_impl(self._chip_name)
        result = impl.precompile_hal()
        self._sync_public_state()
        return result

    def compile(self, code: str) -> dict[str, Any]:
        """Compile a complete bare-metal `main.c` source string."""
        source_path = _base_module.BUILD_DIR / "main.c"
        source_path.write_text(code, encoding="utf-8")
        impl = self._ensure_impl(self._chip_name)
        result = impl.compile(source_path, self._chip_name)
        self._sync_public_state()
        return _result_to_dict(result)

    def compile_rtos(self, code: str) -> dict[str, Any]:
        """Compile a complete `main.c` source string with FreeRTOS."""
        source_path = _base_module.BUILD_DIR / "main.c"
        source_path.write_text(code, encoding="utf-8")
        impl = self._ensure_impl(self._chip_name)
        result = impl.compile_rtos(source_path, self._chip_name)
        self._sync_public_state()
        return result

    def get_flash_command(self, bin_path: str | Path, chip: str | None = None) -> list[str]:
        """Return the pyOCD flash command for the selected chip."""
        impl = self._ensure_impl(chip or self._chip_name)
        command = impl.get_flash_command(bin_path, chip or self._chip_name)
        self._sync_public_state()
        return command


_refresh_exports()
_autoload_chips()
_refresh_exports()

__all__ = [
    "CHIP_DB",
    "ChipCompiler",
    "CompileResult",
    "Compiler",
    "get_compiler",
    "get_package_mtime",
    "lookup_chip",
    "register",
    "reload_package",
]
