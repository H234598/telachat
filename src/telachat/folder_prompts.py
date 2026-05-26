from __future__ import annotations


def with_folder_context(system_prompt: str, context: str) -> str:
    clean_context = context.strip()
    if not clean_context:
        return system_prompt
    clean_system = system_prompt.strip()
    if clean_system:
        return f"{clean_system}\n\nOrdner-Kontext:\n{clean_context}"
    return f"Ordner-Kontext:\n{clean_context}"


def without_folder_context(system_prompt: str, context: str) -> str:
    clean = system_prompt.strip()
    clean_context = context.strip()
    if not clean_context:
        return clean
    marker = f"Ordner-Kontext:\n{clean_context}"
    if clean == marker:
        return ""
    suffix = f"\n\n{marker}"
    if clean.endswith(suffix):
        return clean[: -len(suffix)].rstrip()
    return clean
