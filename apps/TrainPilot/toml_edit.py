#!/opt/venvs/core/bin/python
import sys, os, json

try:
    import tomlkit
except ImportError:
    print("Installing tomlkit into the active Python environment...", file=sys.stderr)
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "tomlkit==0.15.0"], check=True)
    import tomlkit

# --------- IO helpers ---------
def load_dict(path: str):
    if not path or not isinstance(path, str):
        raise TypeError("load_dict(path): path must be a string")
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return tomlkit.document()
    with open(path, "r", encoding="utf-8") as f:
        return tomlkit.load(f)

def save_dict(path: str, data) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        tomlkit.dump(data, f)

def is_table(value) -> bool:
    return hasattr(value, "get") and hasattr(value, "__setitem__")

def plain_value(value):
    if hasattr(value, "unwrap"):
        return value.unwrap()
    return value

# --------- dotted key utils ---------
def set_key(path: str, dotted_key: str, mode: str, value: str) -> None:
    data = load_dict(path)
    d = data
    parts = dotted_key.split(".")
    for p in parts[:-1]:
        if p not in d or not is_table(d[p]):
            d[p] = tomlkit.table()
        d = d[p]
    last = parts[-1]

    if mode == "raw":
        # try JSON first, then bool/int/float, finally string
        try:
            parsed = json.loads(value)
        except Exception:
            low = value.lower()
            if low in ("true", "false"):
                parsed = (low == "true")
            else:
                try:
                    parsed = int(value)
                except Exception:
                    try:
                        parsed = float(value)
                    except Exception:
                        parsed = value
        d[last] = parsed
    else:
        # mode == "str" (or anything else): force string
        d[last] = value

    save_dict(path, data)

def del_key(path: str, dotted_key: str) -> None:
    data = load_dict(path)
    d = data
    parts = dotted_key.split(".")
    for p in parts[:-1]:
        if p not in d or not is_table(d[p]):
            # nothing to delete
            print("")  # stay silent/harmless
            return
        d = d[p]
    d.pop(parts[-1], None)
    save_dict(path, data)

def get_key(path: str, dotted_key: str) -> None:
    data = load_dict(path)
    d = data
    parts = dotted_key.split(".")
    for p in parts[:-1]:
        if p not in d or not is_table(d[p]):
            print("")  # not found
            return
        d = d[p]
    val = plain_value(d.get(parts[-1], ""))
    if isinstance(val, (dict, list)):
        print(json.dumps(val))
    else:
        print(val)

# --------- CLI ---------
def usage():
    print(
        "Usage:\n"
        "  toml.py set <file> <dotted.key> <str|raw> <value>\n"
        "  toml.py del <file> <dotted.key>\n"
        "  toml.py get <file> <dotted.key>",
        file=sys.stderr,
    )
    sys.exit(1)

def main():
    if len(sys.argv) < 2:
        usage()
    cmd = sys.argv[1]
    if cmd == "set" and len(sys.argv) >= 6:
        _, _, fn, key, mode, val = sys.argv[:6]
        set_key(fn, key, mode, val)
    elif cmd == "del" and len(sys.argv) >= 4:
        _, _, fn, key = sys.argv[:4]
        del_key(fn, key)
    elif cmd == "get" and len(sys.argv) >= 4:
        _, _, fn, key = sys.argv[:4]
        get_key(fn, key)
    else:
        usage()

if __name__ == "__main__":
    main()
