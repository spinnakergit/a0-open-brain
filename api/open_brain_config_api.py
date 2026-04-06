"""API endpoint: Get/set the Open Brain plugin configuration.

URL: POST /api/plugins/open_brain/open_brain_config_api

Secrets are masked on GET. On SET, any incoming field that still contains
the masked marker ('****') is replaced with the existing on-disk value so
the WebUI can safely re-post a partial form without wiping credentials.
"""

import json
import os
from pathlib import Path

import yaml

from helpers.api import ApiHandler, Request, Response


# (path-in-config-dict, display_name) for every secret field we mask/merge.
SECRET_FIELDS = [
    (("supabase", "secret_key"), "Supabase secret key"),
    (("openrouter", "api_key"), "OpenRouter API key"),
]


def _get_config_path() -> Path:
    candidates = [
        Path(__file__).parent.parent / "config.json",
        Path("/a0/usr/plugins/open_brain/config.json"),
        Path("/a0/plugins/open_brain/config.json"),
    ]
    for p in candidates:
        if p.parent.exists():
            return p
    return candidates[-1]


def _mask_value(val: str) -> str:
    if not val:
        return ""
    if len(val) > 8:
        return val[:2] + "****" + val[-2:]
    return "********"


def _dig(d: dict, path: tuple[str, ...]):
    cur = d
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _set(d: dict, path: tuple[str, ...], value) -> None:
    cur = d
    for key in path[:-1]:
        if key not in cur or not isinstance(cur[key], dict):
            cur[key] = {}
        cur = cur[key]
    cur[path[-1]] = value


class OpenBrainConfigApi(ApiHandler):

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    @classmethod
    def requires_csrf(cls) -> bool:
        return True

    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "get")
        if request.method == "GET" or action == "get":
            return self._get_config()
        return self._set_config(input)

    # ---- get ---- #

    def _get_config(self) -> dict:
        try:
            config_path = _get_config_path()
            if config_path.exists():
                with open(config_path, "r") as f:
                    config = json.load(f)
            else:
                default_path = config_path.parent / "default_config.yaml"
                if default_path.exists():
                    with open(default_path, "r") as f:
                        config = yaml.safe_load(f) or {}
                else:
                    config = {}

            masked = json.loads(json.dumps(config))
            for path, _ in SECRET_FIELDS:
                val = _dig(masked, path)
                if isinstance(val, str) and val:
                    _set(masked, path, _mask_value(val))
            return masked
        except Exception:
            return {"error": "Failed to read configuration."}

    # ---- set ---- #

    def _set_config(self, input: dict) -> dict:
        try:
            config = input.get("config", input)
            if not config or config == {"action": "set"}:
                return {"error": "No config provided"}
            config = dict(config)
            config.pop("action", None)

            config_path = _get_config_path()
            config_path.parent.mkdir(parents=True, exist_ok=True)

            existing = {}
            if config_path.exists():
                try:
                    with open(config_path, "r") as f:
                        existing = json.load(f)
                except Exception:
                    existing = {}

            # Preserve secrets that came back masked from the WebUI
            for path, _ in SECRET_FIELDS:
                incoming = _dig(config, path)
                if isinstance(incoming, str) and "****" in incoming:
                    prior = _dig(existing, path)
                    if prior:
                        _set(config, path, prior)
                    else:
                        _set(config, path, "")

            # Atomic write, 0600 perms
            tmp = config_path.with_suffix(".tmp")
            fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as f:
                json.dump(config, f, indent=2)
            os.replace(str(tmp), str(config_path))

            return {"ok": True}
        except Exception:
            return {"error": "Failed to save configuration."}
