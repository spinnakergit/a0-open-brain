"""API endpoint: Open Brain stats for the WebUI dashboard.

URL: POST /api/plugins/open_brain/open_brain_stats_api
"""

from helpers.api import ApiHandler, Request, Response


class OpenBrainStatsApi(ApiHandler):

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    @classmethod
    def requires_csrf(cls) -> bool:
        return True

    async def process(self, input: dict, request: Request) -> dict | Response:
        try:
            from usr.plugins.open_brain.helpers.open_brain_client import (
                OpenBrainClient,
                get_open_brain_config,
                is_configured,
            )

            config = get_open_brain_config()
            ok, reason = is_configured(config)
            if not ok:
                return {"ok": False, "error": reason}

            source = (input.get("source") or "").strip() or None
            client = OpenBrainClient(config)
            try:
                ok, result = await client.thought_stats(source=source)
            finally:
                await client.close()

            if not ok:
                return {"ok": False, "error": result if isinstance(result, str) else "Failed to fetch stats."}
            return {"ok": True, "stats": result}
        except Exception:
            return {"ok": False, "error": "Failed to fetch stats. Check configuration."}
