from __future__ import annotations

from dataclasses import dataclass, replace

from .client import ChatResult, OpenAICompatClient
from .config import AppConfig, Profile, load_config, set_config_theme
from .store import ChatStore, Folder, Message, Session, messages_for_api, title_from_prompt
from .themes import Theme, normalize_theme_name, theme_by_name, theme_labels


@dataclass(frozen=True)
class ChatPayload:
    session: Session
    messages: list[Message]
    answer: str


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

    def prompt_templates(self) -> dict[str, str]:
        return self.config.prompt_templates

    def apply_prompt_template(self, name: str, text: str = "") -> str:
        try:
            template = self.config.prompt_templates[name]
        except KeyError as exc:
            available = ", ".join(sorted(self.config.prompt_templates)) or "<keine>"
            raise KeyError(f"Prompt-Template '{name}' fehlt. Verfuegbar: {available}") from exc
        if "{input}" in template:
            return template.replace("{input}", text.strip())
        clean = text.strip()
        return f"{template}\n\n{clean}".strip() if clean else template

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

    def create_folder(self, name: str, *, system_prompt: str = "") -> Folder:
        return self.store.create_folder(name, system_prompt=system_prompt)

    def folder_system_prompt(self, folder_id: str | None) -> str:
        if not folder_id:
            return self.system_prompt()
        folder = self.store.get_folder(folder_id)
        if folder and folder.system_prompt:
            return folder.system_prompt
        return self.system_prompt()

    def resolve_system_prompt(self, system_prompt: str | None, folder_id: str | None) -> str:
        if system_prompt is None:
            return self.folder_system_prompt(folder_id)
        clean = system_prompt.strip()
        if clean == self.system_prompt().strip():
            return self.folder_system_prompt(folder_id)
        return clean

    def set_folder_system_prompt(self, folder_id: str, system_prompt: str) -> Folder:
        return self.store.update_folder_system_prompt(folder_id, system_prompt)

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
        profile = self.config.profile(profile_name).with_overrides(model=model)
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
        profile = self.config.profile(profile_name).with_overrides(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        session = self.store.get_session(session_id or "") if session_id else None
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
        result = OpenAICompatClient(profile, retries=1).chat(api_messages, stream=False)
        if isinstance(result, ChatResult):
            answer = result.content
        else:
            answer = "".join(result)
        self.store.add_message(session.id, "assistant", answer)
        return ChatPayload(
            session=session,
            messages=self.store.messages(session.id),
            answer=answer,
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
        result = OpenAICompatClient(profile, retries=1).chat(api_messages, stream=False)
        if isinstance(result, ChatResult):
            answer = result.content
        else:
            answer = "".join(result)
        self.store.add_message(session.id, "assistant", answer)
        updated = self.store.get_session(session.id) or session
        return ChatPayload(
            session=updated,
            messages=self.store.messages(session.id),
            answer=answer,
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
