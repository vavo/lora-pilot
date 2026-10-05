"""Explicit, persistent installation of the optional browser editor."""
import fcntl
import hashlib
import os
import platform
import shutil
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen


VERSION = '4.135.0'
# Official coder/code-server GitHub release asset SHA-256 digests.
CHECKSUMS = {
    'amd64': '300ef4e37e469e6368a4673c6a623e1c9ba8a34f42b394fb49c431a8900bc7d1',
    'arm64': 'fe6561798415e709109cb902dca2a57a687240af7d8220f6fa1d01cd2ae0541e',
}
SYSTEM_BINARY = Path('/usr/bin/code-server')
MAX_DOWNLOAD = 512 * 1024 * 1024
MAX_UNPACKED = 2 * 1024 * 1024 * 1024
MAX_MEMBERS = 100000
INSTALL_TIMEOUT = 1200


class InstallError(RuntimeError):
    pass


def binary(workspace: Path) -> Path | None:
    for candidate in (workspace / 'apps/code-server/bin/code-server', SYSTEM_BINARY):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


def architecture() -> str:
    arch = {'x86_64': 'amd64', 'aarch64': 'arm64', 'arm64': 'arm64'}.get(platform.machine())
    if platform.system() != 'Linux' or arch is None:
        raise InstallError('VS Code installation requires Linux amd64 or arm64.')
    return arch


def _check_deadline(deadline: float) -> None:
    if time.monotonic() > deadline:
        raise InstallError('Installation timed out. Retry from Services.')


def _download(url: str, destination: Path, digest: str, deadline: float) -> None:
    hasher = hashlib.sha256()
    size = 0
    with urlopen(url, timeout=30) as response, destination.open('xb') as output:
        while chunk := response.read(1024 * 1024):
            _check_deadline(deadline)
            size += len(chunk)
            if size > MAX_DOWNLOAD:
                raise InstallError('Download exceeds the installation size limit.')
            output.write(chunk)
            hasher.update(chunk)
    if hasher.hexdigest() != digest:
        raise InstallError('Release checksum verification failed. Nothing was installed.')


def _extract(archive: Path, destination: Path, root_name: str, deadline: float) -> Path:
    size = 0
    # The data filter rejects traversal, external links and special files, and
    # strips ownership and privileged permissions. Never use fully_trusted here.
    with tarfile.open(archive, 'r:gz') as bundle:
        for count, member in enumerate(bundle, 1):
            _check_deadline(deadline)
            size += member.size
            if count > MAX_MEMBERS or size > MAX_UNPACKED:
                raise InstallError('Release archive exceeds the installation size limit.')
            if not member.name.startswith(root_name + '/') and member.name != root_name:
                raise InstallError('Unexpected release archive layout.')
            bundle.extract(member, destination, filter='data')
    return destination / root_name


def install(workspace: Path, progress) -> str:
    if binary(workspace):
        return 'Already installed'
    arch = architecture()
    apps = workspace / 'apps'
    apps.mkdir(parents=True, exist_ok=True)
    target = apps / 'code-server'
    # Also protects against another Portal process writing this workspace.
    with (apps / '.code-server-install.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise InstallError('VS Code installation is already running.') from None
        if binary(workspace):
            return 'Already installed'
        if target.exists() or target.is_symlink():
            raise InstallError('The code-server install directory already exists; it was left untouched.')
        if shutil.disk_usage(apps).free < MAX_DOWNLOAD + MAX_UNPACKED:
            raise InstallError('At least 2.5 GiB of free workspace space is needed to install VS Code.')
        deadline = time.monotonic() + INSTALL_TIMEOUT
        root_name = f'code-server-{VERSION}-linux-{arch}'
        url = f'https://github.com/coder/code-server/releases/download/v{VERSION}/{root_name}.tar.gz'
        # Staging on the same volume makes publication atomic. Failed attempts
        # cannot expose half an installation or overwrite editor data.
        with tempfile.TemporaryDirectory(prefix='.code-server-install-', dir=apps) as temp:
            staging = Path(temp)
            archive = staging / 'release.tar.gz'
            progress(f'Downloading VS Code Server {VERSION} (about 235 MB)…')
            _download(url, archive, CHECKSUMS[arch], deadline)
            progress('Checksum verified. Extracting release…')
            release = _extract(archive, staging / 'unpacked', root_name, deadline)
            executable = release / 'bin/code-server'
            progress('Checking installed executable…')
            result = subprocess.run(
                [str(executable), '--config', str(staging / 'version-check.yaml'), '--version'],
                capture_output=True, text=True, timeout=30)
            # First launch can print a config-created notice before the version.
            if result.returncode or not any(line.split()[:1] == [VERSION] for line in result.stdout.splitlines()):
                raise InstallError('The downloaded editor failed its version check.')
            _check_deadline(deadline)
            # Do not overwrite a directory introduced while downloading.
            if target.exists() or target.is_symlink():
                raise InstallError('The install directory changed; it was left untouched.')
            release.rename(target)
        progress('Installed. Use Start service when ready.')
        return VERSION
