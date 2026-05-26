from __future__ import annotations

import time
from dataclasses import dataclass, replace

from .client import ChatResult, OpenAICompatClient, TokenUsage, token_usage_record
from .config import (
    AppConfig,
    ConfigError,
    Profile,
    delete_config_prompt_template,
    load_config,
    rename_config_prompt_template,
    set_config_app_icon,
    set_config_chat_background_image,
    set_config_header_validation,
    set_config_prompt_template,
    set_config_skill_watchdog_enabled,
    set_config_theme,
)
from .folder_prompts import with_folder_context, without_folder_context
from .store import (
    ChatStore,
    Folder,
    Message,
    Session,
    StoreStats,
    messages_for_api,
    title_from_prompt,
)
from .templates import render_prompt_template
from .themes import Theme, normalize_theme_name, theme_by_name, theme_labels


@dataclass(frozen=True)
class ChatPayload:
    session: Session
    messages: list[Message]
    answer: str
    elapsed_seconds: float
    usage: TokenUsage | None = None


class TelachatController:
    def __init__(self) -> None:
        self.config: AppConfig = load_config()
        self.store = ChatStore()
        self.store.delete_empty_sessions()

    def close(self) -> None:
        self.store.delete_empty_sessions()
        self.store.close()

    def profiles(self) -> dict[str, Profile]:
        return self.config.profiles

    def default_profile_name(self) -> str:
        return self.config.default_profile

    def system_prompt(self) -> str:
        return self.config.default_system_prompt

    def theme(self) -> Theme:
        return theme_by_name(self.config.theme)

    def theme_labels(self) -> dict[str, str]:
        return theme_labels()

    def set_theme(self, name: str) -> Theme:
        theme_name = normalize_theme_name(name)
        set_config_theme(theme_name, self.config.path)
        self.config = replace(load_config(self.config.path), theme=theme_name)
        return self.theme()

    def set_app_icon(self, name: str) -> str:
        icon = set_config_app_icon(name, self.config.path)
        self.config = load_config(self.config.path)
        return self.config.app_icon

    def set_chat_background_image(self, path: str) -> str:
        background = set_config_chat_background_image(path, self.config.path)
        self.config = load_config(self.config.path)
        return self.config.chat_background_image or background

    def set_header_validation(self, enabled: bool) -> bool:
        previous = self.config.validate_profile_headers
        set_config_header_validation(enabled, self.config.path)
        try:
            self.config = load_config(self.config.path)
        except ConfigError:
            set_config_header_validation(previous, self.config.path)
            self.config = load_config(self.config.path)
            raise
        return self.config.validate_profile_headers

    def set_skill_watchdog_enabled(self, enabled: bool) -> bool:
        set_config_skill_watchdog_enabled(enabled, self.config.path)
        self.config = load_config(self.config.path)
        return self.config.skill_watchdog_enabled

    def prompt_templates(self) -> dict[str, str]:
        return self.config.prompt_templates

    def set_prompt_template(self, name: str, template: str) -> dict[str, str]:
        set_config_prompt_template(name, template, self.config.path)
        self.config = load_config(self.config.path)
        return self.config.prompt_templates

    def rename_prompt_template(self, old_name: str, new_name: str) -> dict[str, str]:
        rename_config_prompt_template(old_name, new_name, self.config.path)
        self.config = load_config(self.config.path)
        return self.config.prompt_templates

    def delete_prompt_template(self, name: str) -> dict[str, str]:
        delete_config_prompt_template(name, self.config.path)
        self.config = load_config(self.config.path)
        return self.config.prompt_templates

    def apply_prompt_template(
        self,
        name: str,
        text: str = "",
        *,
        values: dict[str, str] | None = None,
    ) -> str:
        try:
            template = self.config.prompt_templates[name]
        except KeyError as exc:
            available = ", ".join(sorted(self.config.prompt_templates)) or "<keine>"
            raise KeyError(f"Prompt-Template '{name}' fehlt. Verfuegbar: {available}") from exc
        return render_prompt_template(template, text, values=values)

    def list_sessions(
        self,
        limit: int = 40,
        *,
        folder_id: str | None = None,
        sort: str = "updated_desc",
        query: str | None = None,
        tag: str | None = None,
        archive: str = "active",
    ) -> list[Session]:
        return self.store.list_sessions(
            limit,
            folder_id=folder_id,
            sort=sort,
            query=query,
            tag=tag,
            archive=archive,
        )

    def list_folders(self) -> list[Folder]:
        return self.store.list_folders()

    def create_folder(
        self,
        name: str,
        *,
        system_prompt: str = "",
        context: str = "",
        default_profile: str = "",
        default_model: str = "",
    ) -> Folder:
        clean_profile, clean_model = self._validated_folder_backend(
            default_profile,
            default_model,
        )
        return self.store.create_folder(
            name,
            system_prompt=system_prompt,
            context=context,
            default_profile=clean_profile,
            default_model=clean_model,
        )

    def folder_system_prompt(self, folder_id: str | None) -> str:
        if not folder_id:
            return self.system_prompt()
        folder = self.store.get_folder(folder_id)
        if folder:
            base = (
                without_folder_context(folder.system_prompt, folder.context)
                if folder.system_prompt
                else self.system_prompt()
            )
            return with_folder_context(base, folder.context)
        return self.system_prompt()

    def folder_system_prompt_for_edit(self, folder_id: str | None) -> str:
        if not folder_id:
            return self.system_prompt()
        folder = self.store.get_folder(folder_id)
        if folder and folder.system_prompt:
            return without_folder_context(folder.system_prompt, folder.context)
        return self.system_prompt()

    def resolve_system_prompt(self, system_prompt: str | None, folder_id: str | None) -> str:
        if system_prompt is None:
            return self.folder_system_prompt(folder_id)
        clean = system_prompt.strip()
        folder = self.store.get_folder(folder_id) if folder_id else None
        if folder:
            folder_base = (
                without_folder_context(folder.system_prompt, folder.context)
                if folder.system_prompt
                else self.system_prompt()
            ).strip()
            clean_base = without_folder_context(clean, folder.context).strip()
            if clean == folder_base or clean_base == folder_base:
                return self.folder_system_prompt(folder_id)
        if clean == self.system_prompt().strip():
            return self.folder_system_prompt(folder_id)
        return clean

    def set_folder_system_prompt(
        self,
        folder_id: str,
        system_prompt: str,
        *,
        from_effective_prompt: bool = False,
    ) -> Folder:
        if from_effective_prompt:
            folder = self.store.get_folder(folder_id)
            if folder:
                system_prompt = without_folder_context(system_prompt, folder.context)
        return self.store.update_folder_system_prompt(folder_id, system_prompt)

    def set_folder_context(self, folder_id: str, context: str) -> Folder:
        return self.store.update_folder_context(folder_id, context)

    def folder_context_for_edit(self, folder_id: str | None) -> str:
        if not folder_id:
            return ""
        folder = self.store.get_folder(folder_id)
        return folder.context if folder else ""

    def folder_backend(self, folder_id: str | None) -> tuple[str, str]:
        if not folder_id:
            return "", ""
        folder = self.store.get_folder(folder_id)
        if folder is None:
            return "", ""
        return folder.default_profile, folder.default_model

    def resolve_profile(
        self,
        profile_name: str | None,
        model: str | None,
        folder_id: str | None = None,
    ) -> Profile:
        folder_profile, folder_model = self.folder_backend(folder_id)
        clean_profile = profile_name.strip() if profile_name else ""
        clean_model = model.strip() if model else ""
        resolved_profile = clean_profile or folder_profile or None
        resolved_model = clean_model or None
        if resolved_model is None and (
            not clean_profile or (folder_profile and folder_profile == clean_profile)
        ):
            resolved_model = folder_model or None
        return self.config.profile(resolved_profile).with_overrides(model=resolved_model)

    def set_folder_backend(
        self,
        folder_id: str,
        default_profile: str,
        default_model: str,
    ) -> Folder:
        clean_profile, clean_model = self._validated_folder_backend(
            default_profile,
            default_model,
        )
        return self.store.update_folder_backend(folder_id, clean_profile, clean_model)

    def _validated_folder_backend(
        self,
        default_profile: str,
        default_model: str,
    ) -> tuple[str, str]:
        clean_profile = default_profile.strip()
        clean_model = default_model.strip()
        if clean_profile:
            profile = self.config.profile(clean_profile).with_overrides(
                model=clean_model or None
            )
            clean_profile = profile.name
        elif clean_model:
            self.config.profile(None).with_overrides(model=clean_model)
        return clean_profile, clean_model

    def move_session(self, session_id: str, folder_id: str | None) -> Session:
        return self.store.move_session(session_id, folder_id)

    def rename_session(self, session_id: str, title: str) -> Session:
        return self.store.update_session_title(session_id, title)

    def delete_session(self, session_id: str) -> None:
        self.store.delete_session(session_id)

    def set_session_pinned(self, session_id: str, pinned: bool) -> Session:
        return self.store.set_session_pinned(session_id, pinned)

    def set_session_archived(self, session_id: str, archived: bool) -> Session:
        return self.store.set_session_archived(session_id, archived)

    def add_session_tags(self, session_id: str, tags: list[str]) -> Session:
        self.store.add_session_tags(session_id, tags)
        session = self.store.get_session(session_id)
        if session is None:
            raise KeyError(session_id)
        return session

    def remove_session_tags(self, session_id: str, tags: list[str]) -> Session:
        self.store.remove_session_tags(session_id, tags)
        session = self.store.get_session(session_id)
        if session is None:
            raise KeyError(session_id)
        return session

    def list_tags(self) -> list[tuple[str, int]]:
        return self.store.list_tags()

    def stats(self) -> StoreStats:
        return self.store.stats()

    def rename_folder(self, folder_id: str, name: str) -> Folder:
        return self.store.update_folder_name(folder_id, name)

    def delete_folder(self, folder_id: str) -> None:
        self.store.delete_folder(folder_id)

    def get_session(self, session_id: str) -> tuple[Session, list[Message]]:
        session = self.store.get_session(session_id)
        if session is None:
            raise KeyError(session_id)
        return session, self.store.messages(session.id)

    def new_session(
        self,
        *,
        profile_name: str | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
        title: str = "Neue Unterhaltung",
        folder_id: str | None = None,
    ) -> tuple[Session, list[Message]]:
        profile = self.resolve_profile(profile_name, model, folder_id)
        resolved_system_prompt = self.resolve_system_prompt(system_prompt, folder_id)
        session = self.store.create_session(
            title=title,
            profile=profile.name,
            model=profile.model,
            system_prompt=resolved_system_prompt,
            folder_id=folder_id,
        )
        return session, []

    def send(
        self,
        *,
        session_id: str | None,
        profile_name: str | None,
        model: str | None,
        system_prompt: str,
        prompt: str,
        folder_id: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ChatPayload:
        clean = prompt.strip()
        if not clean:
            raise ValueError("Nachricht fehlt.")
        session = self.store.get_session(session_id or "") if session_id else None
        profile = self.resolve_profile(
            profile_name,
            model,
            folder_id if session is None else None,
        )
        profile = profile.with_overrides(
            temperature=temperature,
            max_tokens=max_tokens,
        )
        effective_system_prompt = system_prompt
        if session is None:
            effective_system_prompt = self.resolve_system_prompt(system_prompt, folder_id)
            session = self.store.create_session(
                title=title_from_prompt(clean),
                profile=profile.name,
                model=profile.model,
                system_prompt=effective_system_prompt,
                folder_id=folder_id,
            )
        elif session.title == "Neue Unterhaltung":
            session = self.store.update_session_title(session.id, title_from_prompt(clean))
        if session.profile != profile.name or session.model != profile.model:
            session = self.store.update_session_backend(session.id, profile.name, profile.model)

        self.store.add_message(session.id, "user", clean)
        history = self.store.messages(session.id, limit=self.config.max_history_messages)
        api_messages = messages_for_api(effective_system_prompt, history)
        started = time.perf_counter()
        result = OpenAICompatClient(profile, retries=1).chat(api_messages, stream=False)
        elapsed = time.perf_counter() - started
        if isinstance(result, ChatResult):
            answer = result.content
            usage = result.usage
        else:
            answer = "".join(result)
            usage = None
        self.store.add_message(
            session.id,
            "assistant",
            answer,
            metadata=_assistant_message_metadata(usage),
        )
        return ChatPayload(
            session=session,
            messages=self.store.messages(session.id),
            answer=answer,
            elapsed_seconds=elapsed,
            usage=usage,
        )

    def regenerate(
        self,
        *,
        session_id: str,
        profile_name: str | None,
        model: str | None,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ChatPayload:
        session = self.store.get_session(session_id)
        if session is None:
            raise KeyError(session_id)
        profile = self.config.profile(profile_name or session.profile).with_overrides(
            model=model or session.model or None,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if session.profile != profile.name or session.model != profile.model:
            session = self.store.update_session_backend(session.id, profile.name, profile.model)
        self.store.delete_last_assistant_message(session.id)
        history = self.store.messages(session.id, limit=self.config.max_history_messages)
        if not any(message.role == "user" for message in history):
            raise ValueError("Keine Nutzernachricht zum Neu-Generieren vorhanden.")
        api_messages = messages_for_api(system_prompt or session.system_prompt, history)
        started = time.perf_counter()
        result = OpenAICompatClient(profile, retries=1).chat(api_messages, stream=False)
        elapsed = time.perf_counter() - started
        if isinstance(result, ChatResult):
            answer = result.content
            usage = result.usage
        else:
            answer = "".join(result)
            usage = None
        self.store.add_message(
            session.id,
            "assistant",
            answer,
            metadata=_assistant_message_metadata(usage),
        )
        updated = self.store.get_session(session.id) or session
        return ChatPayload(
            session=updated,
            messages=self.store.messages(session.id),
            answer=answer,
            elapsed_seconds=elapsed,
            usage=usage,
        )

    def edit_last_user_message(
        self,
        session_id: str,
        content: str,
    ) -> tuple[Session, list[Message]]:
        self.store.edit_last_user_message(session_id, content)
        session = self.store.get_session(session_id)
        if session is None:
            raise KeyError(session_id)
        return session, self.store.messages(session.id)

    def fork_session(
        self,
        session_id: str,
        title: str | None = None,
    ) -> tuple[Session, list[Message]]:
        fork = self.store.fork_session(session_id, title)
        return fork, self.store.messages(fork.id)

    def doctor(self, profile_name: str | None = None, model: str | None = None) -> list[str]:
        profile = self.config.profile(profile_name).with_overrides(model=model)
        return OpenAICompatClient(profile, retries=1).list_models()

    def export_markdown(self, session_id: str) -> str:
        return self.store.export_markdown(session_id)


def _assistant_message_metadata(usage: TokenUsage | None) -> dict[str, object] | None:
    record = token_usage_record(usage)
    return {"usage": record} if record else None
