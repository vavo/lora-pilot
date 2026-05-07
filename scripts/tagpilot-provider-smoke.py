#!/usr/bin/env python3
import argparse
import base64
import binascii
import json
import os
import shlex
import struct
import sys
import time
import urllib.error
import urllib.request
import zlib
from pathlib import Path
from typing import Any


def make_png(width: int = 32, height: int = 32) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        crc = binascii.crc32(kind + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)

    rows = []
    for y in range(height):
        pixels = bytearray()
        for x in range(width):
            pixels.extend(((40 + x * 4) % 256, (80 + y * 4) % 256, 160))
        rows.append(b"\x00" + bytes(pixels))
    raw = b"".join(rows)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


PNG_FIXTURE = make_png()
DATA_URL = "data:image/png;base64," + base64.b64encode(PNG_FIXTURE).decode("ascii")
PROMPT = "Return exactly three comma-separated visual tags for this tiny test image."
TIMEOUT = 90
SMOKE_MAX_OUTPUT_TOKENS = 128


def load_secrets() -> None:
    for path in (Path("/workspace/config/secrets.env"), Path("workspace/config/secrets.env")):
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("export "):
                stripped = stripped[len("export ") :]
            if "=" not in stripped:
                continue
            key, raw = stripped.split("=", 1)
            key = key.strip()
            if key in os.environ:
                continue
            try:
                parts = shlex.split(raw)
                value = parts[0] if parts else ""
            except ValueError:
                value = raw.strip().strip("'\"")
            if value:
                os.environ[key] = value


def post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> tuple[int, dict[str, str], Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={**headers, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = resp.read().decode("utf-8", errors="replace")
            return resp.status, dict(resp.headers), json.loads(data)
    except urllib.error.HTTPError as exc:
        data = exc.read().decode("utf-8", errors="replace")
        try:
            parsed: Any = json.loads(data)
        except Exception:
            parsed = data
        return exc.code, dict(exc.headers), parsed


def error_text(data: Any) -> str:
    if isinstance(data, dict):
        err = data.get("error")
        if isinstance(err, dict):
            return str(err.get("message") or err)
        if err:
            return str(err)
        for key in ("message", "detail"):
            if data.get(key):
                return str(data[key])
    return str(data)


def extract_responses_text(data: Any) -> str:
    if isinstance(data, dict):
        text = data.get("output_text")
        if isinstance(text, str) and text.strip():
            return text.strip()
        for item in data.get("output", []) or []:
            for content in item.get("content", []) or []:
                if isinstance(content, dict) and content.get("type") in {"output_text", "text"}:
                    text = content.get("text")
                    if isinstance(text, str) and text.strip():
                        return text.strip()
    return ""


def smoke_openai() -> tuple[bool, str]:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        return False, "skipped: OPENAI_API_KEY missing"
    models = [os.environ.get("TAGPILOT_OPENAI_MODEL", "").strip() or "gpt-5.4-mini", "gpt-5.5"]
    seen: set[str] = set()
    for model in [m for m in models if not (m in seen or seen.add(m))]:
        status, headers, data = post_json(
            "https://api.openai.com/v1/responses",
            {
                "model": model,
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": PROMPT},
                            {"type": "input_image", "image_url": DATA_URL},
                        ],
                    }
                ],
                "max_output_tokens": SMOKE_MAX_OUTPUT_TOKENS,
            },
            {"Authorization": f"Bearer {key}"},
        )
        if status < 400:
            text = extract_responses_text(data)
            if not text:
                return False, f"failed: OpenAI {model} response missing text"
            return True, f"ok: OpenAI responses {model}; request={headers.get('x-request-id', '-')}; text={text[:80]}"
        if status not in {400, 404}:
            return False, f"failed: OpenAI {model} HTTP {status}: {error_text(data)}"
    return False, "failed: OpenAI models unavailable"


def smoke_gemini() -> tuple[bool, str]:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        return False, "skipped: GEMINI_API_KEY missing"
    models = ["gemini-3-flash-preview", "gemini-3.1-flash-lite-preview"]
    versions = [v.strip().strip("/") for v in os.environ.get("TAGPILOT_GEMINI_API_VERSIONS", "v1,v1beta").split(",") if v.strip()]
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": PROMPT},
                    {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(PNG_FIXTURE).decode("ascii")}},
                ]
            }
        ],
        "generationConfig": {"maxOutputTokens": SMOKE_MAX_OUTPUT_TOKENS, "temperature": 0},
    }
    last = ""
    for model in models:
        for version in versions:
            status, _, data = post_json(
                f"https://generativelanguage.googleapis.com/{version}/models/{model}:generateContent",
                payload,
                {"x-goog-api-key": key},
            )
            if status < 400:
                text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                if not str(text).strip():
                    return False, f"failed: Gemini {version} {model} response missing text"
                return True, f"ok: Gemini {version} {model}; text={str(text)[:80]}"
            last = f"{version} {model} HTTP {status}: {error_text(data)}"
            if status not in {400, 404}:
                return False, f"failed: Gemini {last}"
    return False, f"failed: Gemini {last}"


def smoke_grok() -> tuple[bool, str]:
    key = os.environ.get("XAI_API_KEY", "").strip()
    if not key:
        return False, "skipped: XAI_API_KEY missing"
    models = ["grok-4.3", "grok-4"]
    for model in models:
        status, _, data = post_json(
            "https://api.x.ai/v1/responses",
            {
                "model": model,
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_image", "image_url": DATA_URL, "detail": "high"},
                            {"type": "input_text", "text": PROMPT},
                        ],
                    }
                ],
                "max_output_tokens": SMOKE_MAX_OUTPUT_TOKENS,
                "store": False,
            },
            {"Authorization": f"Bearer {key}"},
        )
        if status < 400:
            text = extract_responses_text(data)
            if not text:
                return False, f"failed: xAI responses {model} response missing text"
            return True, f"ok: xAI responses {model}; text={text[:80]}"
        if status in {401, 403, 429}:
            return False, f"failed: xAI responses {model} HTTP {status}: {error_text(data)}"

        status, _, data = post_json(
            "https://api.x.ai/v1/chat/completions",
            {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": PROMPT},
                            {"type": "image_url", "image_url": {"url": DATA_URL}},
                        ],
                    }
                ],
                "max_tokens": SMOKE_MAX_OUTPUT_TOKENS,
                "stream": False,
                "temperature": 0,
            },
            {"Authorization": f"Bearer {key}"},
        )
        if status < 400:
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not str(text).strip():
                return False, f"failed: xAI chat {model} response missing text"
            return True, f"ok: xAI chat {model}; text={str(text)[:80]}"
    return False, "failed: xAI models unavailable"


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test TagPilot cloud provider API compatibility.")
    parser.add_argument("--provider", choices=("all", "openai", "gemini", "grok"), default="all")
    parser.add_argument("--require-all", action="store_true", help="fail if any provider key is missing")
    args = parser.parse_args()

    load_secrets()
    checks = {
        "openai": smoke_openai,
        "gemini": smoke_gemini,
        "grok": smoke_grok,
    }
    selected = checks if args.provider == "all" else {args.provider: checks[args.provider]}
    failed = False
    for name, fn in selected.items():
        start = time.monotonic()
        ok, message = fn()
        elapsed = time.monotonic() - start
        print(f"{name}: {message} ({elapsed:.1f}s)")
        if not ok and (args.require_all or not message.startswith("skipped:")):
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
