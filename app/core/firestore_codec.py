"""Firestore field-naming and None-handling helpers.

Single Responsibility: pure dict/key transformation, nothing else. This
module knows nothing about Firestore clients, documents, or models — it
just translates between the snake_case our Pydantic models use and the
camelCase convention Firestore documents are stored in, and normalizes how
`None` is handled on the way in and out.

Kept dependency-free on purpose so app.services.base (and any future
Firestore-backed service) can use it without pulling in a client, and so
every test here runs with no mocking at all.
"""

from __future__ import annotations

import re
from typing import Any, cast

_CAMEL_BOUNDARY = re.compile(r"_([a-z0-9])")
_SNAKE_BOUNDARY = re.compile(r"(?<!^)(?=[A-Z])")


def snake_to_camel(key: str) -> str:
    """'owner_uid' -> 'ownerUid'. Keys without underscores are unchanged."""
    return _CAMEL_BOUNDARY.sub(lambda match: match.group(1).upper(), key)


def camel_to_snake(key: str) -> str:
    """'ownerUid' -> 'owner_uid'. Already-lowercase keys are unchanged."""
    return _SNAKE_BOUNDARY.sub("_", key).lower()


def keys_to_camel_case(value: Any) -> Any:
    """Recursively convert dict keys from snake_case to camelCase.

    None-safe: `None` passes through unchanged rather than raising, at any
    depth. Lists are walked so nested documents (e.g. a model's
    `destinations`/`flights` sub-lists) are converted too; non-dict,
    non-list scalars are returned as-is.
    """
    if isinstance(value, dict):
        return {snake_to_camel(k): keys_to_camel_case(v) for k, v in value.items()}
    if isinstance(value, list):
        return [keys_to_camel_case(item) for item in value]
    return value


def keys_to_snake_case(value: Any) -> Any:
    """Inverse of keys_to_camel_case. Equally None-safe."""
    if isinstance(value, dict):
        return {camel_to_snake(k): keys_to_snake_case(v) for k, v in value.items()}
    if isinstance(value, list):
        return [keys_to_snake_case(item) for item in value]
    return value


def encode_for_write(
    data: dict[str, Any], *, exclude_none: bool = False
) -> dict[str, Any]:
    """Prepare a snake_case model dict for a Firestore write.

    exclude_none matters for partial updates: Firestore's `.update()` only
    touches the keys you pass it. An included `None` explicitly nulls that
    field; an *omitted* key leaves the existing value untouched. So:
      - full-document writes (`create_document`/`save_model`) should use
        the default `exclude_none=False` — every field the model has,
        null or not, belongs in a fresh document.
      - partial writes (`update_document`) should pass `exclude_none=True`
        so an unset/None field on the caller's side doesn't unintentionally
        wipe out an existing value in Firestore.

    Only top-level None-stripping is applied — nested maps are replaced
    wholesale on a Firestore update regardless, so partial-update semantics
    don't extend to nested keys.
    """
    working = {k: v for k, v in data.items() if not (exclude_none and v is None)}
    # keys_to_camel_case is Any-typed (it recurses through nested lists/dicts
    # of unknown shape); a dict[str, Any] input always yields a dict back.
    return cast(dict[str, Any], keys_to_camel_case(working))


def decode_from_read(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Prepare a raw Firestore document for Pydantic model validation.

    None-safe at the document level: a document that doesn't exist (or a
    field that's genuinely null) is passed straight through rather than
    raising, so callers can do `model_class.model_validate(data)` only
    after checking for None themselves — same pattern as before.
    """
    if data is None:
        return None
    return cast(dict[str, Any], keys_to_snake_case(data))
