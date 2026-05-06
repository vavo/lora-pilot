from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from typing import Any, Mapping


MAX_OUTPUT_TOKENS = 300


class TagPilotAIError(RuntimeError):
    pass


class MissingProviderKey(TagPilotAIError):
    pass


class ProviderRequestError(TagPilotAIError):
    pass


@dataclass(frozen=True)
class ProviderSpec:
    id: str
    name: str
    secret_name: str
    models: tuple[str, ...]


PROVIDERS: dict[str, ProviderSpec] = {
    "openai": ProviderSpec(
        id="openai",
        name="OpenAI",
        secret_name="OPENAI_API_KEY",
        models=("gpt-5.4-mini", "gpt-5.5"),
    ),
    "gemini": ProviderSpec(
        id="gemini",
        name="Gemini",
        secret_name="GEMINI_API_KEY",
        models=("gemini-3-flash-preview", "gemini-3.1-flash-lite-preview"),
    ),
    "grok": ProviderSpec(
        id="grok",
        name="Grok",
        secret_name="XAI_API_KEY",
        models=("grok-4.3", "grok-4"),
    ),
}


def normalize_provider(provider: str) -> str:
    provider_id = (provider or "").strip().lower()
    if provider_id not in PROVIDERS:
        raise ValueError(f"Unsupported TagPilot provider: {provider}")
    return provider_id


def provider_spec(provider: str) -> ProviderSpec:
    return PROVIDERS[normalize_provider(provider)]


def secret_name_for_provider(provider: str) -> str:
    return provider_spec(provider).secret_name


def provider_status(environ: Mapping[str, str] | None = None) -> dict[str, list[dict[str, Any]]]:
    env = environ if environ is not None else os.environ
    providers = []
    for spec in PROVIDERS.values():
        providers.append(
            {
                "id": spec.id,
                "name": spec.name,
                "configured": bool((env.get(spec.secret_name) or "").strip()),
                "models": list(_candidate_models(spec, env)),
            }
        )
    return {"providers": providers}


def require_provider_key(provider: str, environ: Mapping[str, str] | None = None) -> str:
    spec = provider_spec(provider)
    env = environ if environ is not None else os.environ
    key = (env.get(spec.secret_name) or "").strip()
    if not key:
        raise MissingProviderKey(f"{spec.secret_name} is not configured")
    return key


def build_openai_payload(
    *,
    prompt: str,
    image_bytes: bytes,
    mime_type: str,
    model: str,
) -> dict[str, Any]:
    return {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": _data_url(image_bytes, mime_type)},
                ],
            }
        ],
        "max_output_tokens": MAX_OUTPUT_TOKENS,
    }


def extract_openai_text(data: Mapping[str, Any]) -> str:
    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()
    for item in data.get("output", []) or []:
        if not isinstance(item, Mapping):
            continue
        for content in item.get("content", []) or []:
            if isinstance(content, Mapping) and content.get("type") in {"output_text", "text"}:
                text = content.get("text")
                if isinstance(text, str) and text.strip():
                    return text.strip()
    raise ProviderRequestError("OpenAI response missing text")


async def generate(
    *,
    provider: str,
    mode: str,
    prompt: str,
    image_bytes: bytes,
    mime_type: str,
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    provider_id = normalize_provider(provider)
    if mode not in {"tags", "caption"}:
        raise ValueError("mode must be tags or caption")
    if not image_bytes:
        raise ValueError("image is required")
    resolved_prompt = prompt.strip() or _default_prompt(mode)
    env = environ if environ is not None else os.environ

    if provider_id == "openai":
        return await _generate_openai(resolved_prompt, image_bytes, mime_type, env)
    if provider_id == "gemini":
        return await _generate_gemini(resolved_prompt, image_bytes, mime_type, env)
    if provider_id == "grok":
        return await _generate_grok(resolved_prompt, image_bytes, mime_type, env)
    raise ValueError(f"Unsupported TagPilot provider: {provider}")


def _candidate_models(spec: ProviderSpec, environ: Mapping[str, str]) -> tuple[str, ...]:
    if spec.id == "openai":
        override = (environ.get("TAGPILOT_OPENAI_MODEL") or "").strip()
        if override and override not in spec.models:
            return (override, *spec.models)
    return spec.models


def _default_prompt(mode: str) -> str:
    if mode == "caption":
        return "Provide a detailed natural-language caption for LoRA training."
    return "Provide detailed comma-separated tags for LoRA training."


def _data_url(image_bytes: bytes, mime_type: str) -> str:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime_type or 'application/octet-stream'};base64,{encoded}"


def _gemini_payload(prompt: str, image_bytes: bytes, mime_type: str) -> dict[str, Any]:
    return {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type or "application/octet-stream",
                            "data": base64.b64encode(image_bytes).decode("ascii"),
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "maxOutputTokens": MAX_OUTPUT_TOKENS,
            "temperature": 0,
        },
    }


def _grok_payload(prompt: str, image_bytes: bytes, mime_type: str, model: str) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": _data_url(image_bytes, mime_type)}},
                ],
            }
        ],
        "max_tokens": MAX_OUTPUT_TOKENS,
        "stream": False,
        "temperature": 0,
    }


def _extract_gemini_text(data: Mapping[str, Any], model: str) -> str:
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as exc:
        raise ProviderRequestError(f"Gemini response missing content ({model})") from exc
    if not isinstance(text, str) or not text.strip():
        raise ProviderRequestError(f"Gemini response missing content ({model})")
    return text.strip()


def _extract_grok_text(data: Mapping[str, Any], model: str) -> str:
    try:
        text = data["choices"][0]["message"]["content"]
    except Exception as exc:
        raise ProviderRequestError(f"Grok response missing content ({model})") from exc
    if not isinstance(text, str) or not text.strip():
        raise ProviderRequestError(f"Grok response missing content ({model})")
    return text.strip()


def _parse_response_error(data: Any) -> str:
    if isinstance(data, Mapping):
        err = data.get("error")
        if isinstance(err, Mapping):
            message = err.get("message")
            if message:
                return str(message)
            return str(dict(err))
        if err:
            return str(err)
        for key in ("message", "detail"):
            if data.get(key):
                return str(data[key])
    return str(data)


async def _generate_openai(
    prompt: str,
    image_bytes: bytes,
    mime_type: str,
    environ: Mapping[str, str],
) -> dict[str, str]:
    import httpx

    key = require_provider_key("openai", environ)
    model = _candidate_models(PROVIDERS["openai"], environ)[0]
    payload = build_openai_payload(
        prompt=prompt,
        image_bytes=image_bytes,
        mime_type=mime_type,
        model=model,
    )
    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
        )
    if resp.status_code >= 400:
        try:
            err = _parse_response_error(resp.json())
        except Exception:
            err = resp.text
        raise ProviderRequestError(f"OpenAI error ({model}): {err}")
    return {"text": extract_openai_text(resp.json()), "provider": "openai", "model": model}


async def _generate_gemini(
    prompt: str,
    image_bytes: bytes,
    mime_type: str,
    environ: Mapping[str, str],
) -> dict[str, str]:
    import httpx

    key = require_provider_key("gemini", environ)
    payload = _gemini_payload(prompt, image_bytes, mime_type)
    last_error = ""
    async with httpx.AsyncClient(timeout=90.0) as client:
        for model in PROVIDERS["gemini"].models:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent",
                params={"key": key},
                headers={"Content-Type": "application/json"},
                json=payload,
            )
            if resp.status_code < 400:
                return {"text": _extract_gemini_text(resp.json(), model), "provider": "gemini", "model": model}
            try:
                err = _parse_response_error(resp.json())
            except Exception:
                err = resp.text
            low = str(err).lower()
            if resp.status_code == 404 and ("not found" in low or "not supported" in low):
                last_error = f"{model}: {err}"
                continue
            if resp.status_code == 400 and "api key" in low and "invalid" in low:
                raise ProviderRequestError("Gemini API key is invalid")
            if resp.status_code in {401, 403}:
                raise ProviderRequestError(f"Gemini auth error ({model}): {err}")
            if resp.status_code == 429:
                raise ProviderRequestError(f"Gemini rate limited ({model})")
            raise ProviderRequestError(f"Gemini error ({model}): {err}")
    raise ProviderRequestError(f"Gemini error: no compatible model available. {last_error}".strip())


async def _generate_grok(
    prompt: str,
    image_bytes: bytes,
    mime_type: str,
    environ: Mapping[str, str],
) -> dict[str, str]:
    import httpx

    key = require_provider_key("grok", environ)
    last_error = ""
    async with httpx.AsyncClient(timeout=90.0) as client:
        for model in PROVIDERS["grok"].models:
            resp = await client.post(
                "https://api.x.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=_grok_payload(prompt, image_bytes, mime_type, model),
            )
            if resp.status_code < 400:
                return {"text": _extract_grok_text(resp.json(), model), "provider": "grok", "model": model}
            try:
                err = _parse_response_error(resp.json())
            except Exception:
                err = resp.text
            low = str(err).lower()
            missing_model = resp.status_code == 404 and (
                "does not exist" in low or "not found" in low or "not have access" in low
            )
            if missing_model:
                last_error = f"{model}: {err}"
                continue
            raise ProviderRequestError(f"Grok error ({model}): {err}")
    raise ProviderRequestError(f"Grok error: no compatible model available. {last_error}".strip())
