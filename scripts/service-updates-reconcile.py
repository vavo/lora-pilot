#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
import tomllib
from datetime import datetime
from pathlib import Path
from typing import Optional

SERVICE_UPDATE_SPECS: dict[str, dict[str, str]] = {
    "invoke": {"kind": "pip", "python_bin": "/opt/venvs/invoke/bin/python", "package": "invokeai"},
    "comfy": {"kind": "git", "repo_dir": "/opt/pilot/repos/ComfyUI"},
    "kohya": {"kind": "git", "repo_dir": "/opt/pilot/repos/kohya_ss"},
    "diffpipe": {"kind": "git", "repo_dir": "/opt/pilot/repos/diffusion-pipe"},
    "ai-toolkit": {"kind": "git", "repo_dir": "/opt/pilot/repos/ai-toolkit"},
}


def run_cmd_capture(cmd: list[str], timeout: int = 45) -> str:
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
    )
    out = (result.stdout or "").strip()
    if result.returncode != 0:
        raise RuntimeError(out or f"Command failed ({result.returncode}): {' '.join(cmd)}")
    return out


def run_cmd_stream(cmd: list[str]) -> None:
    print(f"$ {' '.join(cmd)}", flush=True)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip("\n")
        if line:
            print(line, flush=True)
    proc.stdout.close()
    rc = proc.wait()
    if rc != 0:
        raise RuntimeError(f"Command failed ({rc}): {' '.join(cmd)}")


def pip_installed_version(python_bin: str, package: str) -> Optional[str]:
    py = Path(python_bin)
    if not py.exists():
        return None
    code = (
        "import importlib.metadata as m\n"
        f"print(m.version({package!r}))\n"
    )
    try:
        return run_cmd_capture([str(py), "-c", code], timeout=12).strip() or None
    except Exception:
        return None


def git_current_branch(repo: Path) -> Optional[str]:
    try:
        branch = run_cmd_capture(["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"], timeout=12)
    except Exception:
        return None
    if branch and branch != "HEAD":
        return branch
    try:
        remote_head = run_cmd_capture(
            ["git", "-C", str(repo), "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
            timeout=12,
        )
        if remote_head.startswith("origin/"):
            return remote_head.split("/", 1)[1]
    except Exception:
        pass
    return None


def git_local_sha(repo: Path) -> Optional[str]:
    try:
        return run_cmd_capture(["git", "-C", str(repo), "rev-parse", "HEAD"], timeout=12)
    except Exception:
        return None


def service_marker(name: str, spec: dict[str, str]) -> Optional[str]:
    kind = spec.get("kind", "")
    if kind == "pip":
        py = spec.get("python_bin", "")
        pkg = spec.get("package", "")
        if not py or not pkg:
            return None
        return pip_installed_version(py, pkg)
    if kind == "git":
        repo = Path(spec.get("repo_dir", ""))
        if not repo.exists():
            return None
        return git_local_sha(repo)
    return None


def append_rollback(
    log_path: Path,
    *,
    service: str,
    kind: str,
    target: Optional[str],
    before: Optional[str],
    after: Optional[str],
    state: str,
    error: Optional[str] = None,
) -> None:
    payload: dict[str, object] = {
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "service": service,
        "kind": kind,
        "reason": "boot_reconcile",
        "state": state,
        "target": target,
        "before": before,
        "after": after,
    }
    if error:
        payload["error"] = error
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=True) + "\n")


def run_reconcile(config_path: Path, rollback_log_path: Path) -> int:
    if not config_path.exists():
        print(f"[service-updates] config not found: {config_path}; skipping", flush=True)
        return 0

    try:
        cfg = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[service-updates] failed to parse config: {e}", file=sys.stderr, flush=True)
        return 1

    if not isinstance(cfg, dict) or not bool(cfg.get("enabled", False)):
        print("[service-updates] disabled; skipping", flush=True)
        return 0

    services = cfg.get("services", {})
    if not isinstance(services, dict):
        print("[service-updates] no services section; skipping", flush=True)
        return 0

    failures = 0
    for name, service_cfg in services.items():
        if not isinstance(name, str):
            continue
        if not isinstance(service_cfg, dict):
            continue
        if not bool(service_cfg.get("auto_update", False)):
            continue
        spec = SERVICE_UPDATE_SPECS.get(name)
        if not spec:
            print(f"[service-updates] {name}: unsupported (image-managed)", flush=True)
            continue

        kind = spec.get("kind", "unknown")
        target = None
        before = service_marker(name, spec)

        try:
            print(f"[service-updates] {name}: starting update", flush=True)
            if kind == "pip":
                python_bin = spec.get("python_bin", "")
                package = spec.get("package", "")
                target = str(service_cfg.get("target_version", "") or "").strip()
                pkg_ref = f"{package}=={target}" if target else package
                run_cmd_stream([python_bin, "-m", "pip", "install", "--no-cache-dir", "--upgrade", pkg_ref])
            elif kind == "git":
                repo = Path(spec.get("repo_dir", ""))
                target = str(service_cfg.get("target_ref", "") or "").strip()
                if not target:
                    target = git_current_branch(repo) or "main"
                run_cmd_stream(["git", "-C", str(repo), "fetch", "--depth", "1", "origin", target])
                run_cmd_stream(["git", "-C", str(repo), "pull", "--ff-only", "origin", target])
            else:
                print(f"[service-updates] {name}: unknown update kind {kind}; skipping", flush=True)
                continue

            after = service_marker(name, spec)
            append_rollback(
                rollback_log_path,
                service=name,
                kind=kind,
                target=target,
                before=before,
                after=after,
                state="done",
            )
            print(f"[service-updates] {name}: update complete", flush=True)
        except Exception as e:
            failures += 1
            after = service_marker(name, spec)
            append_rollback(
                rollback_log_path,
                service=name,
                kind=kind,
                target=target,
                before=before,
                after=after,
                state="error",
                error=str(e),
            )
            print(f"[service-updates] {name}: update failed: {e}", file=sys.stderr, flush=True)

    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile service versions on boot")
    parser.add_argument(
        "--config",
        default="/workspace/config/service-updates.toml",
        help="Path to service updates TOML config",
    )
    parser.add_argument(
        "--rollback-log",
        default="/workspace/config/service-updates-rollback.jsonl",
        help="Path to rollback JSONL log",
    )
    args = parser.parse_args()
    return run_reconcile(Path(args.config), Path(args.rollback_log))


if __name__ == "__main__":
    raise SystemExit(main())

