"""Persistent Comfy access policy, also read by the Comfy launcher."""
import hashlib
import hmac
import json
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


if __name__ == "__main__":
    import sys
    # An unreadable/corrupt policy stops startup instead of exposing the port.
    print("127.0.0.1" if read_policy(Path(sys.argv[1]))["enabled"] else "0.0.0.0")
