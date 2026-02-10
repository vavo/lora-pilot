import os
import time

from dotenv import load_dotenv
from PIL import Image


def resolve_path(path: str) -> str:
    return os.path.abspath(os.path.expanduser(os.path.expandvars(path)))


load_dotenv()

# Get directories from environment variables or use defaults
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DEFAULT_DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = resolve_path(os.environ.get("MEDIAPILOT_OUTPUT_DIR", os.path.join(DEFAULT_DATA_DIR, "output")))
THUMBS_DIR = resolve_path(os.environ.get("MEDIAPILOT_THUMBS_DIR", os.path.join(DEFAULT_DATA_DIR, "thumbs")))
INVOKEAI_DIR = resolve_path(os.environ.get("MEDIAPILOT_INVOKEAI_DIR", os.path.join(DEFAULT_DATA_DIR, "invokeai")))
THUMB_EXT = ".webp"

def make_thumb(full_path, thumb_path):
    if not os.path.exists(thumb_path):
        os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
        try:
            img = Image.open(full_path)
            img.thumbnail((300, 300))
            img.save(thumb_path, "WEBP", quality=80, method=6)
            return True
        except Exception as e:
            print(f"Failed to create thumb for {full_path}: {e}")
            return False
    return False

def pregenerate_thumbnails():
    start_time = time.time()
    generated_count = 0

    print("Starting thumbnail generation...")

    # --- Process main output directory (and its subdirectories) ---
    print(f"Scanning {OUTPUT_DIR}...")
    for root, _, files in os.walk(OUTPUT_DIR):
        if "_thumbs" in root:
            continue

        for filename in files:
            if not filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                continue

            full_path = os.path.join(root, filename)
            
            # Determine the correct relative path for the thumbnail
            relative_path = os.path.relpath(full_path, OUTPUT_DIR)
            thumb_path = os.path.join(THUMBS_DIR, relative_path + THUMB_EXT)

            if make_thumb(full_path, thumb_path):
                generated_count += 1
                if generated_count % 100 == 0:
                    print(f"Generated {generated_count} thumbnails...")

    # --- Process InvokeAI directory ---
    print(f"Scanning {INVOKEAI_DIR}...")
    if os.path.exists(INVOKEAI_DIR):
        for filename in os.listdir(INVOKEAI_DIR):
            if not filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                continue
            
            full_path = os.path.join(INVOKEAI_DIR, filename)
            thumb_path = os.path.join(THUMBS_DIR, "InvokeAI", filename + THUMB_EXT)

            if make_thumb(full_path, thumb_path):
                generated_count += 1
                if generated_count % 100 == 0:
                    print(f"Generated {generated_count} thumbnails...")

    end_time = time.time()
    print(f"\nFinished pre-generating thumbnails.")
    print(f"Generated {generated_count} new thumbnails in {end_time - start_time:.2f} seconds.")

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(THUMBS_DIR, exist_ok=True)
    os.makedirs(INVOKEAI_DIR, exist_ok=True)
    pregenerate_thumbnails()
