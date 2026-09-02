import re
import uuid


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value)
    return value.strip("-") or uuid.uuid4().hex[:8]


def unique_slug(base_value: str, exists_fn) -> str:
    """Generate a unique slug using exists_fn(candidate) -> bool."""
    base = slugify(base_value)
    candidate = base
    suffix = 1
    while exists_fn(candidate):
        suffix += 1
        candidate = f"{base}-{suffix}"
    return candidate
