"""
network_handler.py: Fetch OpenCore, kexts and patches from their upstream releases

Nothing third-party is bundled with the app. Every payload is downloaded
from the project that publishes it and cached under the data directory.
"""

import json
import shutil
import logging
import zipfile
import urllib.request
import urllib.error
from pathlib import Path
from typing import Callable, Optional

from . import constants as const_module


USER_AGENT = f"{const_module.APP_ID}/{const_module.APP_VERSION}"


class DownloadError(Exception):
    pass


class NetworkHandler:

    def __init__(self, global_constants, progress: Optional[Callable[[str, int, int], None]] = None) -> None:
        self.constants = global_constants
        self.progress = progress
        self._releases = {}
        self.constants.ensure_paths()

    # ---- primitives ----

    def _request(self, url: str, accept: str = "*/*") -> urllib.request.Request:
        headers = {"User-Agent": USER_AGENT, "Accept": accept}
        if self.constants.github_token and "api.github.com" in url:
            headers["Authorization"] = f"Bearer {self.constants.github_token}"
        return urllib.request.Request(url, headers=headers)

    def get_json(self, url: str):
        try:
            with urllib.request.urlopen(self._request(url, "application/vnd.github+json"), timeout=30) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code == 403 and "api.github.com" in url:
                raise DownloadError("GitHub API rate limit reached. Wait an hour, or set GITHUB_TOKEN.") from e
            raise DownloadError(f"{url}: HTTP {e.code}") from e
        except urllib.error.URLError as e:
            raise DownloadError(f"{url}: {e.reason}") from e

    def download(self, url: str, destination: Path, label: str = "") -> Path:
        destination = Path(destination)
        if destination.exists() and destination.stat().st_size > 0:
            return destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        partial = destination.with_suffix(destination.suffix + ".part")
        logging.info(f"- Downloading {label or destination.name}")
        try:
            with urllib.request.urlopen(self._request(url), timeout=60) as resp, open(partial, "wb") as out:
                total = int(resp.headers.get("Content-Length") or 0)
                done = 0
                while True:
                    chunk = resp.read(1 << 16)
                    if not chunk:
                        break
                    out.write(chunk)
                    done += len(chunk)
                    if self.progress:
                        self.progress(label or destination.name, done, total)
        except (urllib.error.URLError, OSError) as e:
            partial.unlink(missing_ok=True)
            raise DownloadError(f"Failed to download {url}: {e}") from e
        if partial.stat().st_size == 0:
            partial.unlink()
            raise DownloadError(f"Downloaded file is empty: {url}")
        partial.replace(destination)
        return destination

    # ---- GitHub releases ----

    def latest_release(self, repo: str) -> dict:
        if repo in self._releases:
            return self._releases[repo]
        self._releases[repo] = self._latest_release(repo)
        return self._releases[repo]

    def _latest_release(self, repo: str) -> dict:
        cache = self.constants.cache_path / "releases" / (repo.replace("/", "_") + ".json")
        try:
            data = self.get_json(f"https://api.github.com/repos/{repo}/releases/latest")
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(data))
            return data
        except DownloadError:
            if cache.exists():
                logging.info(f"- Offline: using cached release info for {repo}")
                return json.loads(cache.read_text())
            raise

    def release_asset(self, repo: str, matcher: Callable[[str], bool]) -> Path:
        release = self.latest_release(repo)
        for asset in release.get("assets", []):
            if matcher(asset["name"]):
                dest = self.constants.cache_path / "payloads" / repo.replace("/", "_") / release["tag_name"] / asset["name"]
                return self.download(asset["browser_download_url"], dest, f"{repo.split('/')[1]} {release['tag_name']}")
        raise DownloadError(f"No matching release asset in {repo} ({release.get('tag_name')})")

    def extract(self, archive: Path) -> Path:
        target = archive.with_suffix("")
        marker = target / ".extracted"
        if marker.exists():
            return target
        if target.exists():
            shutil.rmtree(target)
        with zipfile.ZipFile(archive) as zf:
            for member in zf.infolist():
                # Refuse paths that would escape the target folder
                resolved = (target / member.filename).resolve()
                if not str(resolved).startswith(str(target.resolve())):
                    raise DownloadError(f"Unsafe path in {archive.name}: {member.filename}")
            zf.extractall(target)
            self._restore_modes(zf, target)
        marker.touch()
        return target

    @staticmethod
    def _restore_modes(zf: zipfile.ZipFile, target: Path) -> None:
        # zipfile drops Unix permissions; macserial/ocvalidate need +x on Linux
        for member in zf.infolist():
            mode = (member.external_attr >> 16) & 0o777
            if mode:
                try:
                    (target / member.filename).chmod(mode)
                except OSError:
                    pass

    def fetch_text(self, url: str, cache_name: str) -> bytes:
        dest = self.constants.cache_path / "files" / cache_name
        try:
            with urllib.request.urlopen(self._request(url), timeout=30) as resp:
                data = resp.read()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            return data
        except (urllib.error.URLError, OSError) as e:
            if dest.exists():
                logging.info(f"- Offline: using cached {cache_name}")
                return dest.read_bytes()
            raise DownloadError(f"Failed to download {url}: {e}") from e
