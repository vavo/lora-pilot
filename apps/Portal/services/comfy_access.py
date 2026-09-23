"""Persistent Comfy access policy, also read by the Comfy launcher."""
import hashlib
import hmac
import json
import os
from urllib.parse import urlsplit
from pathlib import Path


def read_policy(path: Path) -> dict:
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        return {"enabled": False, "token_hash": ""}
    if not isinstance(data, dict) or type(data.get("enabled")) is not bool:
        raise ValueError("Invalid Comfy access policy")
    digest = data.get("token_hash", "")
    if not isinstance(digest, str) or (digest and (len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest))):
        raise ValueError("Invalid Comfy API token hash")
    return {"enabled": data["enabled"], "token_hash": digest}


def token_matches(authorization: str, policy: dict) -> bool:
    scheme, _, token = authorization.partition(" ")
    return bool(policy["token_hash"] and scheme.lower() == "bearer" and token and
                hmac.compare_digest(hashlib.sha256(token.encode()).hexdigest(), policy["token_hash"]))


INTERNAL_HEADER = "X-LoRA-Pilot-Comfy-Internal"


def internal_headers(url: str = "") -> dict:
    """Authenticate only first-party requests to this container's Comfy listener."""
    if url:
        target = urlsplit(url)
        if (target.scheme != "http" or target.hostname not in {"127.0.0.1", "localhost"}
                or target.port != int(os.environ.get("COMFY_PORT", "5555"))
                or target.username or target.password):
            return {}
    config = Path(os.environ.get("WORKSPACE_ROOT", "/workspace")) / "config"
    if not read_policy(config / "comfy-access.json")["enabled"]:
        return {}
    settings_path = Path(os.environ.get("CONTROLPILOT_SETTINGS_PATH", str(config / "controlpilot-settings.json")))
    settings = json.loads(settings_path.read_text())
    password_hash = settings.get("password_hash")
    if (settings.get("password_enabled") is not True or not isinstance(password_hash, str)
            or not password_hash.strip()):
        raise ValueError("Comfy protection requires a ControlPilot password")
    secret = settings.get("session_secret")
    if not isinstance(secret, str) or not secret.strip():
        raise ValueError("Comfy internal credential is unavailable")
    token = hmac.new(secret.encode(), b"lora-pilot:comfy-internal:v1", hashlib.sha256).hexdigest()
    return {INTERNAL_HEADER: token}


def direct_access_middleware():
    from aiohttp import web

    @web.middleware
    async def authenticate(request, handler):
        try:
            expected = internal_headers()
        except (OSError, ValueError, TypeError, AttributeError):
            return web.json_response({"detail": "ComfyUI access policy unavailable"}, status=503,
                                     headers={"Cache-Control": "no-store"})
        if expected and not hmac.compare_digest(
                request.headers.get(INTERNAL_HEADER, "").encode(), expected[INTERNAL_HEADER].encode()):
            return web.json_response({"detail": "Open ComfyUI through the ControlPilot gateway"},
                                     status=401, headers={"Cache-Control": "no-store"})
        return await handler(request)

    return authenticate


def install_direct_access(server_path: Path) -> None:
    """Install before Comfy imports its server; incompatible updates fail startup."""
    source = server_path.read_text()
    target = "        self.app = web.Application(client_max_size=max_upload_size, middlewares=middlewares)"
    replacement = ("        from comfy_access import direct_access_middleware\n"
                   "        middlewares.insert(0, direct_access_middleware())\n" + target)
    if source.count(replacement) == 1:
        return
    if source.count(target) != 1:
        raise ValueError("ComfyUI server changed; cannot install access protection")
    server_path.write_text(source.replace(target, replacement, 1))

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 4 and sys.argv[2] == "--install":
        install_direct_access(Path(sys.argv[3]))
    # An unreadable/corrupt policy stops startup instead of exposing the port.
    print("127.0.0.1" if read_policy(Path(sys.argv[1]))["enabled"] else "0.0.0.0")
