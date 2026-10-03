"""Read-only, bounded dataset inspection. Findings are advice, never repairs."""
import hashlib
import os
import stat
import time
from pathlib import Path

from PIL import Image

IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}
CAPTION_EXTENSIONS = {'.txt', '.caption'}


def review_dataset(root, minimum_side=512):
    root = Path(root)
    findings, images, captions, hashes = [], {}, {}, {}
    deadline, remaining = time.monotonic() + 45, 2 * 1024 ** 3
    complete, visited = True, 0

    def report(kind, path, message):
        findings.append(dict(kind=kind, file=path.relative_to(root).as_posix(), message=message))

    for base, dirs, names in os.walk(root, followlinks=False):
        for name in list(dirs):
            path = Path(base) / name
            if path.is_symlink():
                dirs.remove(name)
                report('unsafe', path, 'Symbolic link: training cannot use this folder.')
        for name in sorted(names):
            visited += 1
            if visited > 5000 or time.monotonic() > deadline:
                complete = False
                break
            path = Path(base) / name
            if path.is_symlink():
                report('unsafe', path, 'Symbolic link: training cannot use this file.')
                continue
            extension = path.suffix.lower()
            if extension not in IMAGE_EXTENSIONS | CAPTION_EXTENSIONS:
                continue
            try:
                with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), 'rb') as stream:
                    info = os.fstat(stream.fileno())
                    if not stat.S_ISREG(info.st_mode):
                        report('unsafe', path, 'Not a regular file.')
                        continue
                    if extension in CAPTION_EXTENSIONS:
                        captions.setdefault(path.with_suffix(''), []).append(path)
                        if not stream.read(65536).strip():
                            report('empty_caption', path, 'Caption is empty.')
                        continue
                    images[path] = path.with_suffix('')
                    if info.st_size > 32 * 1024 ** 2 or info.st_size > remaining:
                        report('unchecked', path, 'Image exceeds the review size limit.')
                        complete = False
                        continue
                    remaining -= info.st_size
                    digest = hashlib.file_digest(stream, 'sha256').hexdigest()
                    if digest in hashes:
                        report('duplicate', path, 'Exact copy of ' + hashes[digest])
                    else:
                        hashes[digest] = path.relative_to(root).as_posix()
                    stream.seek(0)
                    with Image.open(stream) as image:
                        if image.width * image.height > 40_000_000:
                            report('unchecked', path, 'Image exceeds the review pixel limit.')
                            complete = False
                            continue
                        image.load()
                        if min(image.size) < minimum_side:
                            report('small', path, f'{image.width} × {image.height}; short side below {minimum_side}px.')
            except (OSError, ValueError, Image.DecompressionBombError):
                report('unreadable', path, 'File could not be read as a supported image or caption.')
        if visited > 5000 or time.monotonic() > deadline:
            break
    for path, stem in images.items():
        if stem not in captions:
            report('missing_caption', path, 'No matching .txt or .caption file.')
    if complete:
        stems = set(images.values())
        for stem, paths in captions.items():
            if stem not in stems:
                for path in paths:
                    report('orphan_caption', path, 'No matching supported image.')
    counts = {kind: sum(item['kind'] == kind for item in findings) for kind in sorted({item['kind'] for item in findings})}
    return dict(dataset=root.name, images=len(images), complete=complete, counts=counts,
                findings=findings, minimum_side=minimum_side)
