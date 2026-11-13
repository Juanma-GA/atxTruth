"""Deep merge for nested configuration (HR10: never shallow-merge)."""

import copy
from typing import Any


def deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """Return a new dict with `patch` merged into `base`, recursing into nested dicts.

    Keys missing from `patch` keep their value from `base`; non-dict values in `patch` replace
    the base value. Neither input is modified.
    """
    result = copy.deepcopy(base)
    for key, value in patch.items():
        current = result.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            result[key] = deep_merge(current, value)
        else:
            result[key] = copy.deepcopy(value)
    return result
