"""Validation for JSON fields that are limited to safe references/metadata."""

from typing import Any


_SAFE_REFERENCE_KEYS = {
    "id",
    "memory_id",
    "document_id",
    "chunk_id",
    "evidence_id",
    "source_id",
    "source",
    "type",
    "memory_type",
    "provenance",
    "kind",
    "timestamp",
    "created_at",
    "occurred_at",
    "score",
    "confidence",
    "tags",
}


def validate_safe_references(value: Any) -> Any:
    """Allow ID lists or small reference dictionaries, never memory text blobs."""
    if value is None:
        return value
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and len(item) <= 255 and "\n" not in item:
                continue
            _validate_reference_object(item)
        return value
    if isinstance(value, dict):
        _validate_reference_object(value)
        return value
    raise ValueError("Memory references must be a list or object of safe identifiers.")


def _validate_reference_object(value: Any) -> None:
    if not isinstance(value, dict) or not value:
        raise ValueError("Memory references must contain safe identifier metadata.")
    for key, item in value.items():
        if key not in _SAFE_REFERENCE_KEYS:
            raise ValueError("Memory references may contain identifier metadata only.")
        if key == "tags":
            if not isinstance(item, list) or not all(
                isinstance(tag, str) and len(tag) <= 100 for tag in item
            ):
                raise ValueError("Memory reference tags must be short strings.")
        elif not isinstance(item, (str, int, float, bool)) and item is not None:
            raise ValueError("Memory reference values must be scalar metadata.")
        elif isinstance(item, str) and len(item) > 255:
            raise ValueError("Memory reference values must not contain full payloads.")
