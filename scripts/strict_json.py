#!/usr/bin/env python3
"""Strict JSON loading helpers for integrity-critical repository metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class StrictJSONError(ValueError):
    """Raised for duplicate keys, non-finite numbers, or malformed JSON."""


def loads(text: str, *, source: str = "<string>") -> Any:
    """Parse JSON while rejecting constructs hidden by the default decoder."""

    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise StrictJSONError(f"duplicate JSON key {key!r} in {source}")
            result[key] = value
        return result

    def reject_constant(value: str) -> Any:
        raise StrictJSONError(f"non-finite JSON number {value!r} in {source}")

    try:
        return json.loads(
            text,
            object_pairs_hook=object_pairs,
            parse_constant=reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise StrictJSONError(f"invalid JSON in {source}: {exc}") from exc


def load(path: Path) -> Any:
    """Read and strictly parse one UTF-8 JSON file."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise StrictJSONError(f"cannot read JSON file {path}: {exc}") from exc
    return loads(text, source=str(path))
