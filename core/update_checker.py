"""
Verificador de actualizaciones desde GitHub Releases.
"""
import urllib.request
import json
import logging

logger = logging.getLogger(__name__)

CURRENT_VERSION = "1.0.0"
GITHUB_API = "https://api.github.com/repos/principalraulcorreos-spec/ADB-Forensic-Helper-F-Seguraa/releases/latest"
RELEASES_PAGE = "https://github.com/principalraulcorreos-spec/ADB-Forensic-Helper-F-Seguraa/releases"


def check_for_updates() -> tuple[bool, str, str]:
    """
    Verifica si hay una versión más nueva en GitHub.
    Retorna (hay_update, version_nueva, url_descarga).
    """
    try:
        req = urllib.request.Request(
            GITHUB_API,
            headers={"User-Agent": "ADB-Forensic-Helper/1.0"}
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode())

        latest = data.get("tag_name", "").lstrip("v")
        download_url = data.get("html_url", RELEASES_PAGE)

        if latest and _version_newer(latest, CURRENT_VERSION):
            return True, latest, download_url
        return False, latest or CURRENT_VERSION, download_url

    except Exception as e:
        logger.debug(f"Update check: {e}")
        return False, CURRENT_VERSION, RELEASES_PAGE


def _version_newer(latest: str, current: str) -> bool:
    try:
        l = tuple(int(x) for x in latest.split("."))
        c = tuple(int(x) for x in current.split("."))
        return l > c
    except Exception:
        return False
