#!/usr/bin/env python3
"""Strict JSON loading helpers for integrity-critical repository metadata."""

from __future__ import annotations

import json
import math
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


class StrictJSONError(ValueError):
    """Raised for duplicate keys, non-finite numbers, or malformed JSON."""


def loads(text: str, *, source: str = "<string>") -> Any:
    """Parse JSON while rejecting constructs hidden by the default decoder.

    Python's standard decoder accepts the non-standard ``NaN``/``Infinity`` tokens and
    also turns an otherwise valid JSON exponent such as ``1e999`` into positive infinity.
    Both forms are rejected here so integrity metadata never contains a non-finite value.
    """

    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise StrictJSONError(f"duplicate JSON key {key!r} in {source}")
            result[key] = value
        return result

    def reject_constant(value: str) -> Any:
        raise StrictJSONError(f"non-finite JSON number {value!r} in {source}")

    def finite_float(value: str) -> float:
        parsed = float(value)
        if not math.isfinite(parsed):
            raise StrictJSONError(f"non-finite JSON number {value!r} in {source}")
        try:
            exact = Decimal(value)
        except InvalidOperation as exc:
            raise StrictJSONError(f"invalid JSON number {value!r} in {source}") from exc
        if parsed == 0.0 and not exact.is_zero():
            raise StrictJSONError(
                f"JSON number underflows the binary float range {value!r} in {source}"
            )
        return parsed

    try:
        return json.loads(
            text,
            object_pairs_hook=object_pairs,
            parse_constant=reject_constant,
            parse_float=finite_float,
        )
    except StrictJSONError:
        raise
    except json.JSONDecodeError as exc:
        raise StrictJSONError(f"invalid JSON in {source}: {exc}") from exc
    except (OverflowError, RecursionError, ValueError) as exc:
        raise StrictJSONError(f"invalid JSON in {source}: {exc}") from exc


def load(path: Path) -> Any:
    """Read and strictly parse one UTF-8 JSON file."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise StrictJSONError(f"cannot read JSON file {path}: {exc}") from exc
    return loads(text, source=str(path))


def canonical_dumps(value: Any) -> str:
    """Return the repository's byte-stable, newline-terminated JSON encoding."""
    try:
        return json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        ) + "\n"
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise StrictJSONError(f"value cannot be encoded as canonical JSON: {exc}") from exc


def loads_canonical(text: str, *, source: str = "<string>") -> Any:
    """Strictly parse JSON and require the exact canonical repository encoding."""
    value = loads(text, source=source)
    if text != canonical_dumps(value):
        raise StrictJSONError(
            f"noncanonical JSON encoding in {source}; use sorted keys, two-space indentation, "
            "ASCII escapes, and one final newline"
        )
    return value


def load_canonical(path: Path) -> Any:
    """Read one UTF-8 JSON file and require its canonical byte representation."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise StrictJSONError(f"cannot read JSON file {path}: {exc}") from exc
    return loads_canonical(text, source=str(path))
