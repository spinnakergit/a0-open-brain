"""API endpoint: Test the Open Brain connection.

URL: POST /api/plugins/open_brain/open_brain_test

Hits the Supabase `thoughts` table with a 1-row select — verifies URL,
secret key, table existence, and service_role grants in one round trip.
Does not touch OpenRouter (use open_brain_stats for that).
"""

from helpers.api import ApiHandler, Request, Response


class OpenBrainTest(ApiHandler):

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

            client = OpenBrainClient(config)
            try:
                ok, result = await client.ping()
            finally:
                await client.close()

            if not ok:
                return {"ok": False, "error": result if isinstance(result, str) else "Connection test failed."}
            return {"ok": True, "detail": result}
        except Exception:
            return {"ok": False, "error": "Connection test failed. Check credentials and network."}
