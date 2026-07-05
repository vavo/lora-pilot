#!/usr/bin/env python3
import argparse
import configparser
from pathlib import Path
import sys
import tomllib


def load_supervisor(conf_path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    with conf_path.open("r", encoding="utf-8") as f:
        parser.read_file(f)
    return parser


def load_state(state_path: Path) -> dict:
    if not state_path.exists():
        return {}
    with state_path.open("rb") as f:
        data = tomllib.load(f)
    services = data.get("services", {})
    return services if isinstance(services, dict) else {}


def write_state(state_path: Path, parser: configparser.ConfigParser) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["[services]"]
    for section in parser.sections():
        if not section.startswith("program:"):
            continue
        name = section.split(":", 1)[1]
        raw = parser.get(section, "autostart", fallback="true").strip().lower()
        enabled = raw in ("1", "true", "yes", "on")
        lines.append(f'["services"."{name}"]')
        lines.append(f'autostart = {"true" if enabled else "false"}')
        lines.append("")
    state_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def apply_state(parser: configparser.ConfigParser, state: dict) -> dict[str, str]:
    changes: dict[str, str] = {}
    for name, svc_cfg in state.items():
        if not isinstance(svc_cfg, dict):
            continue
        if "autostart" not in svc_cfg:
            continue
        section = f"program:{name}"
        if not parser.has_section(section):
            continue
        desired = "true" if bool(svc_cfg.get("autostart")) else "false"
        current = parser.get(section, "autostart", fallback="").strip().lower()
        if current != desired:
            parser.set(section, "autostart", desired)
            changes[section] = desired
    return changes


def section_name(line: str) -> str | None:
    stripped = line.strip()
    if not stripped.startswith("[") or "]" not in stripped:
        return None
    return stripped[1:stripped.index("]")].strip()


def is_autostart_option(line: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped.startswith(("#", ";")):
        return False
    key = stripped.split("=", 1)[0].split(":", 1)[0].strip().lower()
    return key == "autostart"


def write_autostart_changes(conf_path: Path, changes: dict[str, str]) -> None:
    text = conf_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    out: list[str] = []
    current_section: str | None = None
    written: set[str] = set()

    def write_missing_for_current_section() -> None:
        if current_section in changes and current_section not in written:
            out.append(f"autostart={changes[current_section]}")
            written.add(current_section)

    for line in lines:
        next_section = section_name(line)
        if next_section is not None:
            write_missing_for_current_section()
            current_section = next_section
            out.append(line)
            continue

        if current_section in changes and is_autostart_option(line):
            indent = line[: len(line) - len(line.lstrip())]
            out.append(f"{indent}autostart={changes[current_section]}")
            written.add(current_section)
            continue

        out.append(line)

    write_missing_for_current_section()
    conf_path.write_text("\n".join(out) + ("\n" if text.endswith("\n") or text else ""), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--supervisor-conf", required=True)
    ap.add_argument("--state-file", required=True)
    args = ap.parse_args()

    conf_path = Path(args.supervisor_conf)
    state_path = Path(args.state_file)
    parser = load_supervisor(conf_path)

    if not state_path.exists():
        write_state(state_path, parser)
        print(f"[service-autostart] initialized {state_path}", flush=True)
        return 0

    state = load_state(state_path)
    changes = apply_state(parser, state)
    if changes:
        write_autostart_changes(conf_path, changes)
        print(f"[service-autostart] applied persisted autostart settings from {state_path}", flush=True)
    else:
        print(f"[service-autostart] no autostart changes needed", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
