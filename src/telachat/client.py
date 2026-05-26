from __future__ import annotations

import json
import socket
import subprocess
import re
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from . import __version__
from .config import Profile


class ApiError(RuntimeError):
    pass


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    cached_input_tokens: int | None = None
    reasoning_tokens: int | None = None


@dataclass(frozen=True)
class ChatResult:
    content: str
    raw: dict[str, Any]
    usage: TokenUsage | None = None


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
            "model": self.profile.api_model,
            "messages": messages,
            "max_tokens": self.profile.max_tokens,
            "stream": bool(use_stream),
        }
        if self.profile.send_temperature:
            body["temperature"] = self.profile.temperature
        if self.profile.send_top_p:
            body["top_p"] = self.profile.top_p
        if self.profile.reasoning_effort:
            body["reasoning_effort"] = self.profile.reasoning_effort
        if use_stream:
            return self._stream_chat(body)
        raw = self._request_with_fallback("POST", "/chat/completions", body)
        return ChatResult(
            content=_extract_message_content(raw),
            raw=raw,
            usage=_extract_usage(raw),
        )

    def _responses_chat(self, messages: list[dict[str, str]]) -> ChatResult:
        body = {
            "model": self.profile.api_model,
            "input": [
                {"role": item["role"], "content": item["content"]}
                for item in messages
                if item.get("role") in {"system", "user", "assistant"}
                and item.get("content")
            ],
            "max_output_tokens": self.profile.max_tokens,
        }
        if self.profile.send_temperature:
            body["temperature"] = self.profile.temperature
        if self.profile.send_top_p:
            body["top_p"] = self.profile.top_p
        if self.profile.reasoning_effort:
            body["reasoning"] = {"effort": self.profile.reasoning_effort}
        raw = self._request_with_fallback("POST", "/responses", body)
        return ChatResult(
            content=_extract_response_text(raw),
            raw=raw,
            usage=_extract_usage(raw),
        )

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
        response = self._open_with_fallback("POST", "/chat/completions", body)
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

    def _request_with_fallback(
        self,
        method: str,
        path: str,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        current_body = dict(body)
        last_error: ApiError | None = None
        for _ in range(3):
            try:
                return self._request_json(method, path, current_body)
            except ApiError as exc:
                last_error = exc
                reduced_body = _trim_unsupported_parameter(current_body, str(exc))
                if reduced_body is None:
                    raise
                current_body = reduced_body
        assert last_error is not None
        raise last_error

    def _open_with_fallback(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None,
    ) -> Any:
        current_body = dict(body or {})
        last_error: ApiError | None = None
        for _ in range(3):
            try:
                return self._open(method, path, current_body)
            except ApiError as exc:
                last_error = exc
                reduced_body = _trim_unsupported_parameter(current_body, str(exc))
                if reduced_body is None:
                    raise
                current_body = reduced_body
        assert last_error is not None
        raise last_error

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
            "User-Agent": f"Telachat/{__version__}",
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


def _trim_unsupported_parameter(
    body: dict[str, Any],
    error_message: str,
) -> dict[str, Any] | None:
    lowered = error_message.lower()
    unsupported_markers = (
        "unsupported",
        "unsupported parameter",
        "unrecognized",
        "unknown",
        "invalid parameter",
        "invalid",
        "not supported",
    )
    if not any(marker in lowered for marker in unsupported_markers):
        return None
    candidates: tuple[str, ...] = (
        "temperature",
        "top_p",
        "max_tokens",
        "max_output_tokens",
        "reasoning_effort",
        "reasoning",
    )
    quoted_key = re.search(r"[`'\"]\s*'?([a-z0-9_]+)'?\s*[`'\"]", lowered)
    if quoted_key:
        candidate_key = quoted_key.group(1).strip()
        if candidate_key in candidates and candidate_key in body:
            reduced = dict(body)
            reduced.pop(candidate_key, None)
            return reduced

    for key in candidates:
        if key not in body:
            continue
        if key in lowered:
            reduced = dict(body)
            reduced.pop(key, None)
            return reduced
        if re.search(rf"[\"'`] *{re.escape(key)} *[\"'`]", lowered):
            reduced = dict(body)
            reduced.pop(key, None)
            return reduced
        if re.search(rf"\b{re.escape(key)}\b", lowered):
            reduced = dict(body)
            reduced.pop(key, None)
            return reduced
    return None


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


def _extract_usage(payload: dict[str, Any]) -> TokenUsage | None:
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return None
    input_tokens = _int_or_none(usage.get("input_tokens"))
    output_tokens = _int_or_none(usage.get("output_tokens"))
    if input_tokens is None:
        input_tokens = _int_or_none(usage.get("prompt_tokens"))
    if output_tokens is None:
        output_tokens = _int_or_none(usage.get("completion_tokens"))
    total_tokens = _int_or_none(usage.get("total_tokens"))
    cached_input_tokens = _usage_detail_int(usage, "input_tokens_details", "cached_tokens")
    if cached_input_tokens is None:
        cached_input_tokens = _usage_detail_int(usage, "prompt_tokens_details", "cached_tokens")
    reasoning_tokens = _usage_detail_int(usage, "output_tokens_details", "reasoning_tokens")
    if reasoning_tokens is None:
        reasoning_tokens = _usage_detail_int(
            usage,
            "completion_tokens_details",
            "reasoning_tokens",
        )
    result = TokenUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        cached_input_tokens=cached_input_tokens,
        reasoning_tokens=reasoning_tokens,
    )
    if any(value is not None for value in result.__dict__.values()):
        return result
    return None


def _usage_detail_int(
    usage: dict[str, Any],
    detail_key: str,
    value_key: str,
) -> int | None:
    details = usage.get(detail_key)
    if not isinstance(details, dict):
        return None
    return _int_or_none(details.get(value_key))


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None


def format_token_usage(usage: TokenUsage | None) -> str:
    if usage is None:
        return ""
    parts: list[str] = []
    input_tokens = _int_or_none(usage.input_tokens)
    output_tokens = _int_or_none(usage.output_tokens)
    total_tokens = _int_or_none(usage.total_tokens)
    cached_input_tokens = _int_or_none(usage.cached_input_tokens)
    reasoning_tokens = _int_or_none(usage.reasoning_tokens)
    if input_tokens is not None and output_tokens is not None:
        parts.append(f"{input_tokens} in/{output_tokens} out")
    elif input_tokens is not None:
        parts.append(f"{input_tokens} in")
    elif output_tokens is not None:
        parts.append(f"{output_tokens} out")
    if total_tokens is not None:
        parts.append(f"{total_tokens} total")
    if cached_input_tokens:
        parts.append(f"{cached_input_tokens} cached")
    if reasoning_tokens:
        parts.append(f"{reasoning_tokens} reasoning")
    if not parts:
        return ""
    return "Tokens: " + ", ".join(parts)


def token_usage_record(usage: TokenUsage | None) -> dict[str, int]:
    if usage is None:
        return {}
    record: dict[str, int] = {}
    for name, value in (
        ("input_tokens", usage.input_tokens),
        ("output_tokens", usage.output_tokens),
        ("total_tokens", usage.total_tokens),
        ("cached_input_tokens", usage.cached_input_tokens),
        ("reasoning_tokens", usage.reasoning_tokens),
    ):
        clean = _int_or_none(value)
        if clean is not None:
            record[name] = clean
    return record


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
