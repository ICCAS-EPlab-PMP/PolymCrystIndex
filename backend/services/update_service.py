"""Update checking service for release metadata."""

import json
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class UpdateService:
    """Fetch latest release information with lightweight caching."""

    def __init__(self, settings):
        self.settings = settings
        self._cache_lock = threading.Lock()
        self._cache_payload: Optional[Dict] = None
        self._cache_expires_at = 0.0
        self._version_history_path = Path(__file__).resolve().parents[2] / "frontend" / "public" / "version_history.json"

    def check(self) -> Dict:
        now = time.time()
        with self._cache_lock:
            if self._cache_payload and now < self._cache_expires_at:
                return self._build_response(self._cache_payload)

        resolved = self._resolve_latest_release()
        with self._cache_lock:
            self._cache_payload = resolved
            self._cache_expires_at = now + max(int(self.settings.UPDATE_CHECK_CACHE_TTL_SECONDS), 30)
        return self._build_response(resolved)

    def _resolve_latest_release(self) -> Dict:
        github_error = None
        github_release = self._fetch_github_release()
        if github_release is None:
            github_error = "github_unavailable"

        checked_from = "github"
        release = github_release
        gitee_release = None
        fallback_used = False

        if release is None:
            gitee_release = self._fetch_gitee_release()
            if gitee_release is not None:
                release = gitee_release
                checked_from = "gitee"
                fallback_used = True
            else:
                checked_from = "none"

        published_version = release.get("version") if release else None
        comparison = self._compare_versions(self.settings.VERSION, published_version)
        latest_local_release = self._read_local_latest_release()

        if published_version is None:
            status = "check_unavailable"
        elif comparison < 0:
            status = "update_available"
        elif comparison > 0:
            status = "ahead_of_release"
        else:
            status = "up_to_date"

        return {
            "status": status,
            "checkedFrom": checked_from,
            "fallbackUsed": fallback_used,
            "currentVersion": self.settings.VERSION,
            "latestVersion": published_version,
            "hasUpdate": status == "update_available",
            "isAheadOfRelease": status == "ahead_of_release",
            "officialUrl": self.settings.OFFICIAL_DOWNLOAD_URL,
            "githubUrl": self.settings.GITHUB_RELEASES_PAGE_URL,
            "githubLatestUrl": self.settings.GITHUB_LATEST_RELEASE_URL,
            "giteeUrl": self.settings.GITEE_RELEASES_PAGE_URL or None,
            "releasePageUrl": release.get("releasePageUrl") if release else self.settings.GITHUB_RELEASES_PAGE_URL,
            "publishedAt": release.get("publishedAt") if release else None,
            "localPublishedVersion": latest_local_release,
            "githubAvailable": github_release is not None,
            "giteeAvailable": gitee_release is not None,
            "checkedAt": datetime.now(timezone.utc).isoformat(),
            "githubError": github_error,
        }

    def _build_response(self, payload: Dict) -> Dict:
        return {
            "success": True,
            "data": payload,
        }

    def _fetch_github_release(self) -> Optional[Dict]:
        payload = self._fetch_json(self.settings.GITHUB_RELEASES_API_URL)
        if not payload:
            return None

        version = self._normalize_version(payload.get("tag_name") or payload.get("name"))
        if not version:
            return None

        return {
            "version": version,
            "publishedAt": payload.get("published_at"),
            "releasePageUrl": payload.get("html_url") or self.settings.GITHUB_LATEST_RELEASE_URL,
        }

    def _fetch_gitee_release(self) -> Optional[Dict]:
        if not self.settings.GITEE_TAGS_API_URL:
            return None

        payload = self._fetch_json(self.settings.GITEE_TAGS_API_URL)
        if not isinstance(payload, list) or not payload:
            return None

        candidates = []
        for item in payload:
            version = self._normalize_version(item.get("name") or item.get("tag_name"))
            if not version:
                continue
            candidates.append(version)

        if not candidates:
            return None

        latest_version = candidates[0]
        for candidate in candidates[1:]:
            if self._compare_versions(latest_version, candidate) < 0:
                latest_version = candidate

        return {
            "version": latest_version,
            "publishedAt": None,
            "releasePageUrl": self.settings.GITEE_RELEASES_PAGE_URL or None,
        }

    def _fetch_json(self, url: str):
        try:
            request = Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "PolymCrystIndex/UpdateChecker",
                },
            )
            with urlopen(request, timeout=max(int(self.settings.UPDATE_CHECK_TIMEOUT_SECONDS), 1)) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return json.loads(response.read().decode(charset))
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError, OSError):
            return None

    def _read_local_latest_release(self) -> Optional[str]:
        try:
            payload = json.loads(self._version_history_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return None

        versions: List[str] = []
        for item in payload if isinstance(payload, list) else []:
            version = self._normalize_version(item.get("version"))
            if version:
                versions.append(version)
        if not versions:
            return None

        latest = versions[0]
        for candidate in versions[1:]:
            if self._compare_versions(latest, candidate) < 0:
                latest = candidate
        return latest

    @staticmethod
    def _normalize_version(raw: Optional[str]) -> Optional[str]:
        if not raw:
            return None
        value = str(raw).strip()
        if value.lower().startswith("v"):
            value = value[1:]
        match = re.search(r"\d+(?:\.\d+){0,3}", value)
        return match.group(0) if match else None

    @classmethod
    def _compare_versions(cls, left: Optional[str], right: Optional[str]) -> int:
        if left is None and right is None:
            return 0
        if left is None:
            return -1
        if right is None:
            return 1

        left_parts = cls._version_parts(left)
        right_parts = cls._version_parts(right)
        if left_parts < right_parts:
            return -1
        if left_parts > right_parts:
            return 1
        return 0

    @staticmethod
    def _version_parts(version: str) -> Tuple[int, int, int, int]:
        digits = [int(part) for part in re.findall(r"\d+", version)[:4]]
        while len(digits) < 4:
            digits.append(0)
        return digits[0], digits[1], digits[2], digits[3]
