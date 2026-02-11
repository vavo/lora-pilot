import json
import os
import re
import secrets
import shlex
import tempfile
import zipfile
from copy import deepcopy
from datetime import datetime, timezone
from sqlite3 import connect
from typing import Any, Dict, List, Optional, Set
from urllib.parse import quote

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
from pydantic import BaseModel
import requests
from starlette.background import BackgroundTask

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def resolve_path(path: str) -> str:
    return os.path.abspath(os.path.expanduser(os.path.expandvars(path)))


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default

DEFAULT_DATA_DIR = os.path.join(BASE_DIR, "data")

OUTPUT_DIR = resolve_path(
    os.environ.get("MEDIAPILOT_OUTPUT_DIR", os.path.join(DEFAULT_DATA_DIR, "output"))
)
THUMBS_DIR = resolve_path(
    os.environ.get("MEDIAPILOT_THUMBS_DIR", os.path.join(DEFAULT_DATA_DIR, "thumbs"))
)
INVOKEAI_DIR = resolve_path(
    os.environ.get("MEDIAPILOT_INVOKEAI_DIR", os.path.join(DEFAULT_DATA_DIR, "invokeai"))
)
DB_FILE = resolve_path(
    os.environ.get("MEDIAPILOT_DB_FILE", os.path.join(DEFAULT_DATA_DIR, "data.db"))
)
ACCESS_PASSWORD = os.environ.get("MEDIAPILOT_ACCESS_PASSWORD", "").strip()
AUTH_COOKIE_NAME = os.environ.get("MEDIAPILOT_AUTH_COOKIE_NAME", "mediapilot_auth")
AUTH_COOKIE_SECURE = env_bool("MEDIAPILOT_AUTH_COOKIE_SECURE", False)
AUTH_ENABLED = bool(ACCESS_PASSWORD)
ALLOW_ORIGINS = [
    item.strip()
    for item in os.environ.get("MEDIAPILOT_ALLOW_ORIGINS", "*").split(",")
    if item.strip()
]
MAX_BULK_DOWNLOAD_FILES = env_int("MEDIAPILOT_MAX_BULK_DOWNLOAD_FILES", 500)
MAX_BULK_UPSCALE_FILES = env_int("MEDIAPILOT_MAX_BULK_UPSCALE_FILES", 50)
COMFY_API_URL = os.environ.get("MEDIAPILOT_COMFY_API_URL", "http://127.0.0.1:8188").rstrip("/")
UPSCALE_WORKFLOW_FILE = resolve_path(
    os.environ.get(
        "MEDIAPILOT_UPSCALE_WORKFLOW_FILE",
        os.path.join(BASE_DIR, "comfy_upscale_workflow.json"),
    )
)
UPSCALE_INPUT_PLACEHOLDER = os.environ.get("MEDIAPILOT_UPSCALE_INPUT_PLACEHOLDER", "__INPUT_IMAGE__")
UPSCALE_OUTPUT_PLACEHOLDER = os.environ.get(
    "MEDIAPILOT_UPSCALE_OUTPUT_PLACEHOLDER", "__OUTPUT_PREFIX__"
)
UPSCALE_OUTPUT_PREFIX = os.environ.get("MEDIAPILOT_UPSCALE_OUTPUT_PREFIX", "mediapilot-upscaled")
COMFY_REQUEST_TIMEOUT = env_int("MEDIAPILOT_COMFY_REQUEST_TIMEOUT", 60)
THUMB_EXT = ".webp"
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")

# Ensure base directories exist to avoid empty/failed listings
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(THUMBS_DIR, exist_ok=True)
os.makedirs(INVOKEAI_DIR, exist_ok=True)
db_parent = os.path.dirname(DB_FILE)
if db_parent:
    os.makedirs(db_parent, exist_ok=True)

if not ALLOW_ORIGINS:
    ALLOW_ORIGINS = ["*"]

AUTH_SESSIONS: Set[str] = set()

def get_db():
    return connect(DB_FILE)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS likes (filename TEXT PRIMARY KEY)")
    cur.execute(
        "CREATE TABLE IF NOT EXISTS tags (filename TEXT PRIMARY KEY, folder TEXT NOT NULL)"
    )
    conn.commit()
    conn.close()

init_db()

# ---------------------------------------------------
# APP
# ---------------------------------------------------

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


def is_public_path(path: str) -> bool:
    if path == "/":
        return True
    if path.startswith("/static/"):
        return True
    return path in {"/auth/status", "/auth/login", "/healthz"}


@app.middleware("http")
async def enforce_auth(request: Request, call_next):
    if not AUTH_ENABLED:
        return await call_next(request)

    if request.method == "OPTIONS" or is_public_path(request.url.path):
        return await call_next(request)

    token = request.cookies.get(AUTH_COOKIE_NAME)
    if token and token in AUTH_SESSIONS:
        return await call_next(request)

    return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

# ---------------------------------------------------
# STATIC MOUNTS
# ---------------------------------------------------

class StaticFilesNoCache(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers["Cache-Control"] = "no-store, must-revalidate, max-age=0"
        return response

# ---------------------------------------------------
# STATIC MOUNTS
# ---------------------------------------------------

app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")
app.mount("/thumbs", StaticFiles(directory=THUMBS_DIR), name="thumbs")
app.mount("/invoke", StaticFilesNoCache(directory=INVOKEAI_DIR), name="invoke")

# ---------------------------------------------------
# THUMBNAIL MAKER
# ---------------------------------------------------

def make_thumb(full_path, thumb_path):
    if not os.path.exists(thumb_path):
        os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
        try:
            img = Image.open(full_path)
            img.thumbnail((600, 600))
            img.save(thumb_path, "WEBP", quality=80, method=6)
        except:
            pass

# ---------------------------------------------------
# METADATA
# ---------------------------------------------------

LORA_PROMPT_REGEX = re.compile(r"<lora:([^>:]+)(?::([0-9\.]+))?>", re.IGNORECASE)
STEPS_REGEX = re.compile(r"Steps: (\d+)", re.IGNORECASE)
CFG_REGEX = re.compile(r"CFG scale: ([0-9\.]+)", re.IGNORECASE)
SAMPLER_REGEX = re.compile(r"Sampler: ([^,\n]+)", re.IGNORECASE)
SCHEDULER_REGEX = re.compile(r"Scheduler: ([^,\n]+)", re.IGNORECASE)
NUMERIC_SEARCH_REGEX = re.compile(
    r"^(steps|cfg)\s*(<=|>=|=|:|<|>)\s*(-?\d+(?:\.\d+)?)$",
    re.IGNORECASE,
)


def parse_search_query(search: str) -> Dict[str, Any]:
    raw = (search or "").strip()
    if not raw:
        return {"text_terms": [], "field_terms": {}, "numeric_filters": []}

    try:
        tokens = shlex.split(raw)
    except ValueError:
        tokens = raw.split()

    text_terms: List[str] = []
    field_terms: Dict[str, List[str]] = {}
    numeric_filters: List[Dict[str, Any]] = []

    for token in tokens:
        cleaned = token.strip()
        if not cleaned:
            continue

        numeric_match = NUMERIC_SEARCH_REGEX.match(cleaned)
        if numeric_match:
            field, operator, value = numeric_match.groups()
            numeric_filters.append(
                {
                    "field": field.lower(),
                    "operator": "=" if operator == ":" else operator,
                    "value": float(value),
                }
            )
            continue

        if ":" in cleaned:
            key, value = cleaned.split(":", 1)
            field = key.strip().lower()
            term = value.strip().lower()
            if term and field in {"prompt", "lora", "sampler", "scheduler"}:
                field_terms.setdefault(field, []).append(term)
                continue

        text_terms.append(cleaned.lower())

    return {
        "text_terms": text_terms,
        "field_terms": field_terms,
        "numeric_filters": numeric_filters,
    }


def compare_number(actual: float, operator: str, expected: float) -> bool:
    if operator == "=":
        return abs(actual - expected) < 1e-9
    if operator == ">":
        return actual > expected
    if operator == "<":
        return actual < expected
    if operator == ">=":
        return actual >= expected
    if operator == "<=":
        return actual <= expected
    return False


def metadata_matches_search(metadata: Dict[str, Any], criteria: Dict[str, Any]) -> bool:
    prompt = str(metadata.get("prompt") or "").lower()
    lora = str(metadata.get("lora_name") or "").lower()
    sampler = str(metadata.get("sampler") or "").lower()
    scheduler = str(metadata.get("scheduler") or "").lower()
    steps = metadata.get("steps")
    cfg = metadata.get("cfg")

    searchable_fields = {
        "prompt": prompt,
        "lora": lora,
        "sampler": sampler,
        "scheduler": scheduler,
    }

    for field, terms in criteria.get("field_terms", {}).items():
        haystack = searchable_fields.get(field, "")
        if any(term not in haystack for term in terms):
            return False

    for numeric_filter in criteria.get("numeric_filters", []):
        field = numeric_filter["field"]
        actual_raw = steps if field == "steps" else cfg if field == "cfg" else None
        if actual_raw is None:
            return False
        try:
            actual = float(actual_raw)
        except (TypeError, ValueError):
            return False
        if not compare_number(actual, numeric_filter["operator"], numeric_filter["value"]):
            return False

    combined = " ".join(
        [
            prompt,
            lora,
            sampler,
            scheduler,
            str(steps) if steps is not None else "",
            str(cfg) if cfg is not None else "",
        ]
    ).strip()

    for term in criteria.get("text_terms", []):
        if term not in combined:
            return False

    return True


def parse_json_object(value: Any) -> Optional[Dict[str, Any]]:
    if isinstance(value, dict):
        return value
    if value is None:
        return None
    text = str(value).strip()
    if not text.startswith("{"):
        return None
    try:
        parsed = json.loads(text)
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def normalize_number(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_lora_name(value: Any) -> Optional[str]:
    if not value:
        return None
    name = str(value).strip()
    if not name:
        return None
    if name.lower().endswith(".safetensors"):
        return name[: -len(".safetensors")]
    return name


def extract_comfy_metadata(raw_prompt: Any) -> Dict[str, Any]:
    graph = parse_json_object(raw_prompt)
    if not graph:
        return {}

    nodes: Dict[str, Dict[str, Any]] = {}
    for node_id, node in graph.items():
        if isinstance(node, dict):
            nodes[str(node_id)] = node
    if not nodes:
        return {}

    result: Dict[str, Any] = {}

    def get_node_from_ref(ref: Any) -> Optional[Dict[str, Any]]:
        if isinstance(ref, (list, tuple)) and ref:
            return nodes.get(str(ref[0]))
        if ref is None:
            return None
        return nodes.get(str(ref))

    ksampler = next(
        (
            node
            for node in nodes.values()
            if str(node.get("class_type", "")).lower() in {"ksampler", "ksampleradvanced"}
        ),
        None,
    )
    if ksampler:
        inputs = ksampler.get("inputs", {}) if isinstance(ksampler.get("inputs"), dict) else {}
        steps = normalize_number(inputs.get("steps"))
        cfg = normalize_number(inputs.get("cfg"))
        sampler = inputs.get("sampler_name") or inputs.get("sampler")
        scheduler = inputs.get("scheduler")

        if steps is not None:
            result["steps"] = int(steps)
        if cfg is not None:
            result["cfg"] = cfg
        if sampler:
            result["sampler"] = str(sampler).strip()
        if scheduler:
            result["scheduler"] = str(scheduler).strip()

        positive_node = get_node_from_ref(inputs.get("positive"))
        if positive_node and str(positive_node.get("class_type", "")).lower() == "cliptextencode":
            positive_inputs = (
                positive_node.get("inputs", {})
                if isinstance(positive_node.get("inputs"), dict)
                else {}
            )
            positive_text = positive_inputs.get("text")
            if positive_text:
                result["prompt"] = str(positive_text).strip()

    if "prompt" not in result:
        for node in nodes.values():
            if str(node.get("class_type", "")).lower() != "cliptextencode":
                continue
            meta_title = ""
            if isinstance(node.get("_meta"), dict):
                meta_title = str(node["_meta"].get("title", "")).lower()
            if "negative" in meta_title:
                continue
            inputs = node.get("inputs", {}) if isinstance(node.get("inputs"), dict) else {}
            text = inputs.get("text")
            if text:
                result["prompt"] = str(text).strip()
                break

    lora_loader = next(
        (
            node
            for node in nodes.values()
            if "loraloader" in str(node.get("class_type", "")).lower()
        ),
        None,
    )
    if lora_loader:
        inputs = (
            lora_loader.get("inputs", {})
            if isinstance(lora_loader.get("inputs"), dict)
            else {}
        )
        lora_name = normalize_lora_name(inputs.get("lora_name"))
        lora_strength = normalize_number(
            inputs.get("strength_model", inputs.get("strength"))
        )
        if lora_name:
            result["lora_name"] = lora_name
        if lora_strength is not None:
            result["lora_strength"] = lora_strength

    return result


def extract_metadata(full_path: str) -> dict:
    """
    Extract prompt and various metadata from common SD metadata sources.
    """
    prompt = None
    parameters_text = None
    loras = []
    comfy_meta: Dict[str, Any] = {}

    try:
        with Image.open(full_path) as img:
            info = img.info or {}
            comfy_meta = extract_comfy_metadata(info.get("prompt") or info.get("Prompt"))
            if comfy_meta.get("prompt"):
                prompt = str(comfy_meta["prompt"]).strip()

            # Find the main prompt and a block of text containing other parameters
            for key in ("sd-metadata", "prompt", "Prompt", "parameters", "Description"):
                if key not in info or not info[key]:
                    continue
                if key in ("prompt", "Prompt"):
                    if comfy_meta:
                        continue
                    if parse_json_object(info[key]) is not None:
                        continue

                text_content = str(info[key])
                if key == "sd-metadata":
                    try:
                        meta = json.loads(text_content)
                        if isinstance(meta, dict):
                            if not prompt:
                                for k in ("prompt", "Prompt", "positive_prompt"):
                                    if k in meta and meta[k]:
                                        prompt = str(meta[k])
                            # Use the whole sd-metadata as parameters_text if it's a flat dict,
                            # otherwise look for a specific parameters key.
                            if "parameters" in meta:
                                parameters_text = meta["parameters"]
                            elif not parameters_text:
                                parameters_text = prompt
                    except Exception:
                        if not prompt:
                            prompt = text_content
                else:
                    if not prompt:
                        prompt = text_content
                    if not parameters_text:
                        parameters_text = text_content
            
            if not parameters_text:
                parameters_text = prompt

            # Basic EXIF description (JPEG) as a fallback
            if not prompt:
                try:
                    exif = img.getexif()
                    if exif:
                        desc = exif.get(270)
                        if desc:
                            prompt = str(desc)
                            if not parameters_text:
                                parameters_text = prompt
                except Exception:
                    pass
    except Exception:
        pass

    meta = {"prompt": prompt}
    for field in ("lora_name", "lora_strength", "steps", "cfg", "sampler", "scheduler"):
        if field in comfy_meta:
            meta[field] = comfy_meta[field]

    # Heuristic: parse lora from prompt text if not found in dedicated fields
    if prompt:
        found_loras = LORA_PROMPT_REGEX.findall(prompt)
        for name, strength in found_loras:
            loras.append(
                {
                    "name": name.replace(".safetensors", ""),
                    "strength": float(strength) if strength else 1.0,
                }
            )

    # Parse other parameters from the dedicated text block
    if parameters_text:
        steps_match = STEPS_REGEX.search(parameters_text)
        if steps_match and "steps" not in meta:
            meta["steps"] = int(steps_match.group(1))

        cfg_match = CFG_REGEX.search(parameters_text)
        if cfg_match and "cfg" not in meta:
            meta["cfg"] = float(cfg_match.group(1))

        sampler_match = SAMPLER_REGEX.search(parameters_text)
        if sampler_match and "sampler" not in meta:
            meta["sampler"] = sampler_match.group(1).strip()

        scheduler_match = SCHEDULER_REGEX.search(parameters_text)
        if scheduler_match and "scheduler" not in meta:
            meta["scheduler"] = scheduler_match.group(1).strip()

    # Populate final metadata structure from found loras
    if loras and "lora_name" not in meta:
        meta["lora_name"] = loras[0]["name"]
        if loras[0].get("strength"):
            meta["lora_strength"] = loras[0]["strength"]
        if len(loras) > 1:
            meta["lora_name_2"] = loras[1]["name"]
            if loras[1].get("strength"):
                meta["lora_strength_2"] = loras[1]["strength"]

    return meta


# ---------------------------------------------------
# MODELS
# ---------------------------------------------------


class ImageInfo(BaseModel):
    filename: str
    thumb_url: str
    full_url: str
    liked: bool
    tagged: bool
    prompt: Optional[str] = None
    lora_name: Optional[str] = None
    lora_strength: Optional[float] = None
    steps: Optional[int] = None
    cfg: Optional[float] = None
    sampler: Optional[str] = None
    scheduler: Optional[str] = None
    lora_name_2: Optional[str] = None
    lora_strength_2: Optional[float] = None
    created_at: float


class Paginated(BaseModel):
    page: int
    pages: int
    images: List[ImageInfo]

class CreateFolder(BaseModel):
    name: str


class LoginPayload(BaseModel):
    password: str


class BulkDownloadPayload(BaseModel):
    folder: str = "_root"
    filenames: List[str]


class BulkUpscalePayload(BaseModel):
    folder: str = "_root"
    filenames: List[str]


# ---------------------------------------------------
# AUTH
# ---------------------------------------------------

@app.get("/auth/status")
def auth_status(request: Request):
    if not AUTH_ENABLED:
        return {"enabled": False, "authenticated": True}
    token = request.cookies.get(AUTH_COOKIE_NAME)
    return {"enabled": True, "authenticated": bool(token and token in AUTH_SESSIONS)}


@app.post("/auth/login")
def auth_login(payload: LoginPayload, response: Response):
    if not AUTH_ENABLED:
        return {"ok": True, "enabled": False}

    if payload.password != ACCESS_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = secrets.token_urlsafe(32)
    AUTH_SESSIONS.add(token)
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=AUTH_COOKIE_SECURE,
        path="/",
    )
    return {"ok": True, "enabled": True}


@app.post("/auth/logout")
def auth_logout(request: Request, response: Response):
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if token:
        AUTH_SESSIONS.discard(token)
    response.delete_cookie(key=AUTH_COOKIE_NAME, path="/")
    return {"ok": True}


# ---------------------------------------------------
# FOLDERS
# ---------------------------------------------------


def list_folders():
    folders = set()
    try:
        for root, dirnames, _ in os.walk(OUTPUT_DIR):
            dirnames[:] = [d for d in dirnames if d != "_thumbs" and not d.startswith(".")]
            rel_root = os.path.relpath(root, OUTPUT_DIR)
            if rel_root == ".":
                continue
            folders.add(rel_root.replace(os.sep, "/"))
    except FileNotFoundError:
        # If the output dir doesn't exist yet, treat as empty
        pass

    return ["Untagged", "InvokeAI"] + sorted(folders)


def normalize_folder(folder: str) -> str:
    if folder in ("_root", "InvokeAI"):
        return folder
    norm = os.path.normpath(folder).replace("\\", "/")
    if os.path.isabs(norm) or norm == ".." or norm.startswith("../"):
        raise HTTPException(status_code=400, detail="Invalid folder")
    full_path = os.path.abspath(os.path.join(OUTPUT_DIR, norm))
    if os.path.commonpath([full_path, OUTPUT_DIR]) != OUTPUT_DIR:
        raise HTTPException(status_code=400, detail="Invalid folder")
    return norm

def normalize_new_folder(name: str) -> str:
    cleaned = (name or "").strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="Invalid folder")
    if cleaned in ("Untagged", "InvokeAI", "_root"):
        raise HTTPException(status_code=400, detail="Reserved folder name")
    norm = normalize_folder(cleaned)
    if norm in ("_root", "InvokeAI"):
        raise HTTPException(status_code=400, detail="Reserved folder name")
    return norm


def base_dir_for_folder(folder: str) -> str:
    if folder == "_root":
        return OUTPUT_DIR
    if folder == "InvokeAI":
        return INVOKEAI_DIR
    return os.path.join(OUTPUT_DIR, folder)


def normalize_selected_filename(value: str) -> str:
    cleaned = os.path.basename((value or "").replace("\\", "/").strip())
    if not cleaned or cleaned in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid filename")
    return cleaned


def encode_url_segment(value: str) -> str:
    return quote(str(value), safe="")


def encode_folder_for_url(folder: str) -> str:
    return "/".join(encode_url_segment(part) for part in str(folder).split("/") if part)


def remove_temp_file(path: str):
    try:
        os.remove(path)
    except OSError:
        pass


def sanitize_output_prefix(filename: str) -> str:
    stem = os.path.splitext(filename)[0]
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-")
    if not cleaned:
        cleaned = "image"
    return f"{UPSCALE_OUTPUT_PREFIX}/{cleaned}"


def load_upscale_workflow_template() -> Dict[str, Any]:
    if not os.path.isfile(UPSCALE_WORKFLOW_FILE):
        raise HTTPException(
            status_code=500,
            detail=f"Upscale workflow file not found: {UPSCALE_WORKFLOW_FILE}",
        )
    try:
        with open(UPSCALE_WORKFLOW_FILE, "r", encoding="utf-8") as handle:
            workflow = json.load(handle)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Invalid workflow JSON: {exc}") from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Unable to read workflow file: {exc}") from exc
    if not isinstance(workflow, dict):
        raise HTTPException(status_code=500, detail="Workflow JSON must be an object")
    return workflow


def replace_placeholder(obj: Any, placeholder: str, value: str) -> bool:
    replaced = False
    if isinstance(obj, dict):
        for key, nested in obj.items():
            if isinstance(nested, str):
                if placeholder in nested:
                    obj[key] = nested.replace(placeholder, value)
                    replaced = True
            else:
                replaced = replace_placeholder(nested, placeholder, value) or replaced
    elif isinstance(obj, list):
        for idx, nested in enumerate(obj):
            if isinstance(nested, str):
                if placeholder in nested:
                    obj[idx] = nested.replace(placeholder, value)
                    replaced = True
            else:
                replaced = replace_placeholder(nested, placeholder, value) or replaced
    return replaced


def set_first_load_image_node(workflow: Dict[str, Any], input_image: str) -> bool:
    for node in workflow.values():
        if not isinstance(node, dict):
            continue
        if str(node.get("class_type", "")).lower() != "loadimage":
            continue
        inputs = node.get("inputs")
        if not isinstance(inputs, dict):
            inputs = {}
            node["inputs"] = inputs
        inputs["image"] = input_image
        return True
    return False


def ensure_workflow_input_image(
    workflow: Dict[str, Any],
    input_image: str,
    output_prefix: str,
) -> Dict[str, Any]:
    workflow_copy = deepcopy(workflow)
    replaced_input = replace_placeholder(workflow_copy, UPSCALE_INPUT_PLACEHOLDER, input_image)
    if not replaced_input:
        replaced_input = set_first_load_image_node(workflow_copy, input_image)
    if not replaced_input:
        raise HTTPException(
            status_code=500,
            detail=(
                f'Workflow must include placeholder "{UPSCALE_INPUT_PLACEHOLDER}" '
                "or a LoadImage node"
            ),
        )
    replace_placeholder(workflow_copy, UPSCALE_OUTPUT_PLACEHOLDER, output_prefix)
    return workflow_copy


def upload_image_to_comfy(session: requests.Session, full_path: str, filename: str) -> str:
    upload_url = f"{COMFY_API_URL}/upload/image"
    try:
        with open(full_path, "rb") as handle:
            response = session.post(
                upload_url,
                data={"type": "input", "overwrite": "false"},
                files={"image": (filename, handle)},
                timeout=COMFY_REQUEST_TIMEOUT,
            )
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Unable to read file for upload: {exc}") from exc
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Comfy upload failed: {exc}") from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"Comfy upload error ({response.status_code}): {response.text[:300]}",
        )
    try:
        payload = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Comfy upload returned invalid JSON") from exc

    uploaded_name = str(payload.get("name") or filename)
    subfolder = str(payload.get("subfolder") or "").strip("/")
    if subfolder:
        return f"{subfolder}/{uploaded_name}"
    return uploaded_name


def submit_workflow_to_comfy(session: requests.Session, workflow: Dict[str, Any]) -> str:
    prompt_url = f"{COMFY_API_URL}/prompt"
    try:
        response = session.post(
            prompt_url,
            json={"prompt": workflow},
            timeout=COMFY_REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Comfy prompt submit failed: {exc}") from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"Comfy prompt error ({response.status_code}): {response.text[:300]}",
        )
    try:
        payload = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Comfy prompt returned invalid JSON") from exc

    prompt_id = payload.get("prompt_id")
    if not prompt_id:
        raise HTTPException(status_code=502, detail="Comfy response missing prompt_id")
    return str(prompt_id)


@app.get("/folders")
def get_folders():
    return {"folders": list_folders()}


@app.post("/folders")
def create_folder(payload: CreateFolder):
    folder = normalize_new_folder(payload.name)
    os.makedirs(os.path.join(OUTPUT_DIR, folder), exist_ok=True)
    return {"created": True, "folder": folder}


# ---------------------------------------------------
# IMAGES
# ---------------------------------------------------


@app.get("/images", response_model=Paginated)
def get_images(
    page: int = Query(1),
    limit: int = Query(50),
    folder: str = Query("_root"),
    sort: str = Query("NEWEST"),
    search: str = Query(""),
):
    folder = normalize_folder(folder)
    if folder == "_root":
        base_dir = OUTPUT_DIR
    elif folder == "InvokeAI":
        base_dir = INVOKEAI_DIR
    else:
        base_dir = os.path.join(OUTPUT_DIR, folder)
    if not os.path.exists(base_dir):
        return Paginated(page=1, pages=1, images=[])

    file_entries = []
    for f in os.listdir(base_dir):
        if not f.lower().endswith(IMAGE_EXTS):
            continue
        full_p = os.path.join(base_dir, f)
        file_entries.append((f, os.path.getmtime(full_p)))

    # Sort entries according to requested sort
    sort_upper = (sort or "").upper()
    if sort_upper == "OLDEST":
        file_entries.sort(key=lambda x: x[1])
    elif sort_upper == "ALPHABETICALLY":
        file_entries.sort(key=lambda x: x[0].lower())
    else:  # NEWEST default
        file_entries.sort(key=lambda x: x[1], reverse=True)

    search_criteria = parse_search_query(search)
    metadata_cache: Dict[str, Dict[str, Any]] = {}
    has_search = bool(
        search_criteria["text_terms"]
        or search_criteria["field_terms"]
        or search_criteria["numeric_filters"]
    )
    if has_search:
        filtered_entries = []
        for f, mtime in file_entries:
            full_path = os.path.join(base_dir, f)
            metadata = extract_metadata(full_path)
            metadata_cache[f] = metadata
            if metadata_matches_search(metadata, search_criteria):
                filtered_entries.append((f, mtime))
        file_entries = filtered_entries

    total = len(file_entries)
    pages = max(1, (total + limit - 1) // limit)

    start = (page - 1) * limit
    end = start + limit
    page_files = file_entries[start:end]

    conn = get_db()
    cur = conn.cursor()
    liked = {row[0] for row in cur.execute("SELECT filename FROM likes")}
    conn.close()

    items = []
    for f, mtime in page_files:
        full_path = os.path.join(base_dir, f)
        metadata = metadata_cache.get(f)
        if metadata is None:
            metadata = extract_metadata(full_path)
        safe_filename = encode_url_segment(f)

        if folder == "_root":
            thumb_path = os.path.join(THUMBS_DIR, f + THUMB_EXT)
            thumb_url = f"./thumbs/{safe_filename}{THUMB_EXT}"
            full_url = f"./output/{safe_filename}"
        elif folder == "InvokeAI":
            thumb_path = os.path.join(THUMBS_DIR, "InvokeAI", f + THUMB_EXT)
            thumb_url = f"./thumbs/InvokeAI/{safe_filename}{THUMB_EXT}"
            full_url = f"./invoke/{safe_filename}"
        else:
            thumb_path = os.path.join(THUMBS_DIR, folder, f + THUMB_EXT)
            folder_url = encode_folder_for_url(folder)
            thumb_url = f"./thumbs/{folder_url}/{safe_filename}{THUMB_EXT}"
            full_url = f"./output/{folder_url}/{safe_filename}"

        make_thumb(full_path, thumb_path)

        items.append(
            ImageInfo(
                filename=f,
                full_url=full_url,
                thumb_url=thumb_url,
                liked=(f in liked),
                tagged=(folder != "_root"),
                created_at=mtime,
                **metadata,
            )
        )

    return Paginated(page=page, pages=pages, images=items)

# ---------------------------------------------------
# LIKE
# ---------------------------------------------------

@app.post("/like/{filename}")
def like_file(filename: str):
    filename = normalize_selected_filename(filename)
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO likes(filename) VALUES (?)", (filename,))
    conn.commit()
    conn.close()
    return {"ok": True}

@app.post("/unlike/{filename}")
def unlike_file(filename: str):
    filename = normalize_selected_filename(filename)
    conn = get_db()
    conn.execute("DELETE FROM likes WHERE filename = ?", (filename,))
    conn.commit()
    conn.close()
    return {"ok": True}

# ---------------------------------------------------
# DELETE
# ---------------------------------------------------

@app.delete("/image/{folder:path}/{filename}")
@app.delete("/image/{filename}")
def delete_file(filename: str, folder: str = "_root"):
    filename = normalize_selected_filename(filename)
    folder = normalize_folder(folder)
    if folder == "_root":
        base_dir = OUTPUT_DIR
    elif folder == "InvokeAI":
        base_dir = INVOKEAI_DIR
    else:
        base_dir = os.path.join(OUTPUT_DIR, folder)
    path = os.path.join(base_dir, filename)

    if os.path.exists(path):
        os.remove(path)

    thumb = (
        os.path.join(THUMBS_DIR, filename + THUMB_EXT)
        if folder == "_root"
        else os.path.join(THUMBS_DIR, folder, filename + THUMB_EXT)
    )
    if os.path.exists(thumb):
        os.remove(thumb)

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM likes WHERE filename = ?", (filename,))
    cur.execute("DELETE FROM tags WHERE filename = ?", (filename,))
    conn.commit()
    conn.close()

    return {"deleted": True}

# ---------------------------------------------------
# TAG (MOVE)
# ---------------------------------------------------

@app.post("/tag")
def tag_file(filename: str, old_folder: str, new_folder: str):
    filename = normalize_selected_filename(filename)
    old_folder = normalize_folder(old_folder)
    new_folder = normalize_folder(new_folder)
    if old_folder == "_root":
        old_dir = OUTPUT_DIR
    elif old_folder == "InvokeAI":
        old_dir = INVOKEAI_DIR
    else:
        old_dir = os.path.join(OUTPUT_DIR, old_folder)

    new_dir = OUTPUT_DIR if new_folder == "_root" else os.path.join(OUTPUT_DIR, new_folder)

    os.makedirs(new_dir, exist_ok=True)

    src = os.path.join(old_dir, filename)
    dst = os.path.join(new_dir, filename)

    if os.path.exists(src):
        os.rename(src, dst)

    if old_folder == "_root":
        old_thumb = os.path.join(THUMBS_DIR, filename + THUMB_EXT)
    elif old_folder == "InvokeAI":
        old_thumb = os.path.join(THUMBS_DIR, "InvokeAI", filename + THUMB_EXT)
    else:
        old_thumb = os.path.join(THUMBS_DIR, old_folder, filename + THUMB_EXT)
    if os.path.exists(old_thumb):
        os.remove(old_thumb)

    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO tags(filename, folder) VALUES (?, ?)",
        (filename, new_folder),
    )
    conn.commit()
    conn.close()

    return {"moved": True}


# ---------------------------------------------------
# BULK UPSCALE
# ---------------------------------------------------

@app.post("/upscale/bulk")
def upscale_bulk(payload: BulkUpscalePayload):
    folder = normalize_folder(payload.folder or "_root")
    filenames = payload.filenames or []

    if not filenames:
        raise HTTPException(status_code=400, detail="No files selected")
    if len(filenames) > MAX_BULK_UPSCALE_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files selected (max {MAX_BULK_UPSCALE_FILES})",
        )

    base_dir = base_dir_for_folder(folder)
    workflow_template = load_upscale_workflow_template()

    unique_filenames = []
    seen = set()
    for raw_name in filenames:
        safe_name = normalize_selected_filename(raw_name)
        if safe_name in seen:
            continue
        seen.add(safe_name)
        unique_filenames.append(safe_name)

    submitted = []
    failed = []
    with requests.Session() as session:
        for filename in unique_filenames:
            full_path = os.path.join(base_dir, filename)
            if not os.path.isfile(full_path):
                failed.append({"filename": filename, "error": "File not found"})
                continue
            try:
                comfy_input_image = upload_image_to_comfy(session, full_path, filename)
                workflow = ensure_workflow_input_image(
                    workflow_template,
                    input_image=comfy_input_image,
                    output_prefix=sanitize_output_prefix(filename),
                )
                prompt_id = submit_workflow_to_comfy(session, workflow)
                submitted.append(
                    {
                        "filename": filename,
                        "prompt_id": prompt_id,
                        "comfy_input_image": comfy_input_image,
                    }
                )
            except HTTPException as exc:
                failed.append({"filename": filename, "error": str(exc.detail)})
            except Exception as exc:
                failed.append({"filename": filename, "error": str(exc)})

    if not submitted and failed:
        raise HTTPException(status_code=502, detail={"submitted": [], "failed": failed})

    return {
        "ok": True,
        "queued": len(submitted),
        "submitted": submitted,
        "failed": failed,
    }


# ---------------------------------------------------
# BULK DOWNLOAD
# ---------------------------------------------------

@app.post("/download/bulk")
def download_bulk(payload: BulkDownloadPayload):
    folder = normalize_folder(payload.folder or "_root")
    filenames = payload.filenames or []

    if not filenames:
        raise HTTPException(status_code=400, detail="No files selected")
    if len(filenames) > MAX_BULK_DOWNLOAD_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files selected (max {MAX_BULK_DOWNLOAD_FILES})",
        )

    base_dir = base_dir_for_folder(folder)

    unique_filenames = []
    seen = set()
    for raw_name in filenames:
        safe_name = normalize_selected_filename(raw_name)
        if safe_name in seen:
            continue
        seen.add(safe_name)
        unique_filenames.append(safe_name)

    if not unique_filenames:
        raise HTTPException(status_code=400, detail="No valid files selected")

    temp_zip = tempfile.NamedTemporaryFile(prefix="mediapilot_bulk_", suffix=".zip", delete=False)
    zip_path = temp_zip.name
    temp_zip.close()

    added = 0
    try:
        with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            for filename in unique_filenames:
                full_path = os.path.join(base_dir, filename)
                if not os.path.isfile(full_path):
                    continue
                archive.write(full_path, arcname=filename)
                added += 1

        if added == 0:
            remove_temp_file(zip_path)
            raise HTTPException(status_code=404, detail="No files found")

        folder_slug = "untagged" if folder == "_root" else folder.replace("/", "-")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        archive_name = f"mediapilot-{folder_slug}-{timestamp}.zip"

        return FileResponse(
            path=zip_path,
            media_type="application/zip",
            filename=archive_name,
            background=BackgroundTask(remove_temp_file, zip_path),
        )
    except HTTPException:
        raise
    except Exception:
        remove_temp_file(zip_path)
        raise HTTPException(status_code=500, detail="Failed to create archive")

# ---------------------------------------------------
# SERVE FRONTEND
# ---------------------------------------------------

STATIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))

app.mount("/static", StaticFilesNoCache(directory=STATIC_DIR), name="static")

@app.get("/healthz")
def health():
    return {"ok": True}


@app.get("/")
def root():
    response = FileResponse(os.path.join(STATIC_DIR, "index.html"))
    response.headers["Cache-Control"] = "no-store, must-revalidate, max-age=0"
    return response
