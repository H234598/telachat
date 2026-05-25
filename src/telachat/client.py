from __future__ import annotations

import json
import socket
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from .config import Profile


class ApiError(RuntimeError):
    pass


@dataclass(frozen=True)
class ChatResult:
    content: str
    raw: dict[str, Any]


class OpenAICompatClient:
    def __init__(self, profile: Profile, *, retries: int = 1) -> None:
        self.profile = profile
        self.retries = max(0, retries)

    def list_models(self) -> list[str]:
        if self.profile.api_mode == "codex" or self.profile.base_url == "codex://local":
            return ["codex-cli"]
        payload = self._request_json("GET", "/models", None)
        data = payload.get("data", [])
        models = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and isinstance(item.get("id"), str):
                    models.append(item["id"])
        return models

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        stream: bool | None = None,
    ) -> ChatResult | Iterator[str]:
        if self.profile.api_mode == "codex" or self.profile.base_url == "codex://local":
            return self._codex_chat(messages)
        if self.profile.api_mode == "responses":
            return self._responses_chat(messages)
        use_stream = self.profile.stream if stream is None else stream
        body = {
            "model": self.profile.model,
            "messages": messages,
            "temperature": self.profile.temperature,
            "top_p": self.profile.top_p,
            "max_tokens": self.profile.max_tokens,
            "stream": bool(use_stream),
        }
        if use_stream:
            return self._stream_chat(body)
        raw = self._request_json("POST", "/chat/completions", body)
        return ChatResult(content=_extract_message_content(raw), raw=raw)

    def _responses_chat(self, messages: list[dict[str, str]]) -> ChatResult:
        body = {
            "model": self.profile.model,
            "input": [
                {"role": item["role"], "content": item["content"]}
                for item in messages
                if item.get("role") in {"system", "user", "assistant"}
                and item.get("content")
            ],
            "max_output_tokens": self.profile.max_tokens,
        }
        raw = self._request_json("POST", "/responses", body)
        return ChatResult(content=_extract_response_text(raw), raw=raw)

    def _codex_chat(self, messages: list[dict[str, str]]) -> ChatResult:
        prompt = _messages_to_codex_prompt(messages)
        try:
            completed = subprocess.run(
                [
                    "codex",
                    "exec",
                    "--skip-git-repo-check",
                    "--sandbox",
                    "read-only",
                    prompt,
                ],
                check=False,
                text=True,
                capture_output=True,
                timeout=self.profile.timeout_seconds,
            )
        except FileNotFoundError as exc:
            raise ApiError("codex CLI wurde nicht gefunden.") from exc
        except subprocess.TimeoutExpired as exc:
            raise ApiError("codex CLI lief in ein Timeout.") from exc
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            raise ApiError(f"codex CLI Fehler: {detail[:800]}")
        content = completed.stdout.strip()
        return ChatResult(content=content, raw={"provider": "codex-cli"})

    def _stream_chat(self, body: dict[str, Any]) -> Iterator[str]:
        response = self._open("POST", "/chat/completions", body)
        try:
            for line in response:
                text = line.decode("utf-8", errors="replace").strip()
                if not text or text.startswith(":"):
                    continue
                if not text.startswith("data:"):
                    continue
                data = text[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    payload = json.loads(data)
                except json.JSONDecodeError:
                    continue
                token = _extract_delta_content(payload)
                if token:
                    yield token
        finally:
            response.close()

    def _request_json(
        self, method: str, path: str, body: dict[str, Any] | None
    ) -> dict[str, Any]:
        response = self._open(method, path, body)
        try:
            raw = response.read().decode("utf-8", errors="replace")
        finally:
            response.close()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ApiError(f"API lieferte kein JSON: {raw[:240]}") from exc
        if not isinstance(payload, dict):
            raise ApiError("API lieferte eine unerwartete JSON-Struktur.")
        return payload

    def _open(
        self, method: str, path: str, body: dict[str, Any] | None
    ) -> Any:
        url = f"{self.profile.base_url.rstrip('/')}/{path.lstrip('/')}"
        encoded = None
        if body is not None:
            encoded = json.dumps(body).encode("utf-8")
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "User-Agent": "Telachat/0.1",
        }
        api_key = self.profile.resolved_api_key()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        if self.profile.extra_headers:
            headers.update(self.profile.extra_headers)

        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            request = urllib.request.Request(
                url=url,
                data=encoded,
                headers=headers,
                method=method,
            )
            try:
                return urllib.request.urlopen(
                    request, timeout=self.profile.timeout_seconds
                )
            except urllib.error.HTTPError as exc:
                detail = _read_error_body(exc)
                if 500 <= exc.code < 600 and attempt < self.retries:
                    last_error = exc
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise ApiError(f"HTTP {exc.code} von API: {detail}") from exc
            except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise ApiError(f"API nicht erreichbar: {exc}") from exc
        raise ApiError(f"API nicht erreichbar: {last_error}")


def _extract_message_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ApiError("API-Antwort enthaelt keine choices.")
    first = choices[0]
    if not isinstance(first, dict):
        raise ApiError("API-Antwort enthaelt eine ungueltige choice.")
    message = first.get("message")
    if isinstance(message, dict) and isinstance(message.get("content"), str):
        return message["content"]
    text = first.get("text")
    if isinstance(text, str):
        return text
    raise ApiError("API-Antwort enthaelt keinen Text.")


def _extract_delta_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    delta = first.get("delta")
    if isinstance(delta, dict) and isinstance(delta.get("content"), str):
        return delta["content"]
    message = first.get("message")
    if isinstance(message, dict) and isinstance(message.get("content"), str):
        return message["content"]
    return ""


def _extract_response_text(payload: dict[str, Any]) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str):
        return output_text
    output = payload.get("output")
    parts: list[str] = []
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if isinstance(content, list):
                for chunk in content:
                    if isinstance(chunk, dict):
                        text = chunk.get("text")
                        if isinstance(text, str):
                            parts.append(text)
            elif isinstance(content, str):
                parts.append(content)
    if parts:
        return "".join(parts).strip()
    raise ApiError("Responses-API-Antwort enthaelt keinen Text.")


def _read_error_body(exc: urllib.error.HTTPError) -> str:
    try:
        raw = exc.read().decode("utf-8", errors="replace").strip()
    except Exception:
        raw = ""
    if not raw:
        return exc.reason or "kein Fehlertext"
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return raw[:500]
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str):
                return message
        if isinstance(payload.get("detail"), str):
            return payload["detail"]
    return raw[:500]


def _messages_to_codex_prompt(messages: list[dict[str, str]]) -> str:
    lines = [
        "Du antwortest als Codex in Telachat. Fuehre keine Shell-Kommandos aus, "
        "ausser der Nutzer bittet ausdruecklich darum. Antworte knapp und direkt.",
        "",
    ]
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        if role == "system":
            lines.append(f"System: {content}")
        elif role == "assistant":
            lines.append(f"Assistent bisher: {content}")
        else:
            lines.append(f"Nutzer: {content}")
    return "\n\n".join(lines)
