"""Compiler registry for STM32 chip-family compilers."""

from __future__ import annotations

from typing import TypeVar

from .base import ChipCompiler

CompilerType = TypeVar("CompilerType", bound=type[ChipCompiler])

_REGISTRY: list[type[ChipCompiler]] = []


def register(compiler_cls: CompilerType) -> CompilerType:
    """Register a chip compiler class."""
    if compiler_cls not in _REGISTRY:
        _REGISTRY.append(compiler_cls)
    return compiler_cls


def get_compiler(chip: str) -> ChipCompiler:
    """Return a compiler instance that supports the given chip name."""
    for compiler_cls in _REGISTRY:
        if compiler_cls.supports(chip):
            return compiler_cls()
    raise ValueError(f"No compiler registered for chip: {chip}")

