from __future__ import annotations

from collections.abc import Iterable


def merge_model_choices(
    selected: str,
    live_models: Iterable[str],
    configured_models: Iterable[str],
) -> list[str]:
    merged: list[str] = []
    for model in [selected, *live_models, *configured_models]:
        if model and model not in merged:
            merged.append(model)
    return merged
