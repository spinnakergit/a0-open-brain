"""Open Brain HTTP client.

Talks directly to the user's Open Brain Supabase project + OpenRouter,
using the same patterns as the canonical OB1 MCP edge function:
  - Direct INSERT for capture (matching the MCP server), with optional
    `upsert_thought` RPC for content-fingerprint dedup if installed
  - `match_thoughts(query_embedding, match_threshold, match_count, filter)`
    RPC for semantic search
  - Direct table reads with `metadata @>` filters for list / stats
  - OpenRouter `/embeddings` for vectors, `/chat/completions` for metadata

Reference: https://github.com/NateBJones-Projects/OB1/blob/main/server/index.ts
Recipes: content-fingerprint-dedup, source-filtering.

Design rules:
  - Never raises raw exceptions to the agent. All public methods return
    (ok, payload_or_error) tuples so tools can build sanitized error
    messages without leaking credentials, URLs, or stack traces.
  - Single aiohttp session per client instance; callers must call
    `close()` to release it.
  - All free-text inputs are sanitized via helpers.sanitize before
    hitting the wire.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import aiohttp

logger = logging.getLogger("open_brain_client")


OPENROUTER_BASE = "https://openrouter.ai/api/v1"
DEFAULT_EMBEDDING_MODEL = "openai/text-embedding-3-small"
DEFAULT_EXTRACTION_MODEL = "openai/gpt-4o-mini"

# Metadata-extraction system prompt lifted from OB1 server/index.ts so
# thoughts captured via A0 have the same schema as thoughts captured via
# any other OB1 client.
_METADATA_SYSTEM_PROMPT = """Extract metadata from the user's captured thought. Return JSON with:
- "people": array of people mentioned (empty if none)
- "action_items": array of implied to-dos (empty if none)
- "dates_mentioned": array of dates YYYY-MM-DD (empty if none)
- "topics": array of 1-3 short topic tags (always at least one)
- "type": one of "observation", "task", "idea", "reference", "person_note"
Only extract what's explicitly there."""


# --------------------------------------------------------------------------- #
# Config loading
# --------------------------------------------------------------------------- #


def get_open_brain_config(agent=None) -> dict:
    """Load plugin configuration via the A0 plugin system, with fallback.

    Uses the canonical A0 plugin config pipeline first, then falls back to
    reading config.json directly if the helper is unavailable (e.g., when
    running outside an A0 container for testing).
    """
    try:
        from helpers import plugins  # type: ignore

        config = plugins.get_plugin_config("open_brain", agent=agent)
        if config:
            return config
    except Exception:
        pass

    # Fallback: direct config.json read
    try:
        here = Path(__file__).parent.parent
        for candidate in (here / "config.json", Path("/a0/usr/plugins/open_brain/config.json")):
            if candidate.exists():
                with open(candidate, "r") as f:
                    return json.load(f)
    except Exception:
        pass
    return {}


def is_configured(config: dict) -> tuple[bool, str]:
    """Check if all required credentials are present.

    Returns (ok, reason). On failure, `reason` is agent-safe text — no
    credentials or URLs leaked.
    """
    supabase = config.get("supabase") or {}
    openrouter = config.get("openrouter") or {}
    if not supabase.get("url"):
        return False, "Open Brain is not configured: Supabase URL is missing."
    if not supabase.get("secret_key"):
        return False, "Open Brain is not configured: Supabase secret key is missing."
    if not openrouter.get("api_key"):
        return False, "Open Brain is not configured: OpenRouter API key is missing."
    return True, ""


def _safe_supabase_url(url: str) -> str:
    """Normalize and validate a Supabase URL.

    Handles the common mistake of pasting the Supabase dashboard URL
    (https://supabase.com/dashboard/project/<ref>) instead of the API URL
    (https://<ref>.supabase.co).

    Validates that the final URL is a legitimate *.supabase.co endpoint
    to prevent credential exfiltration via config-hijacked URLs.
    """
    import re
    from urllib.parse import urlparse

    url = (url or "").strip().rstrip("/")
    if not url:
        return url
    # Detect dashboard URL and convert to API URL
    m = re.match(r"https?://supabase\.com/dashboard/project/([a-z0-9]+)", url)
    if m:
        url = f"https://{m.group(1)}.supabase.co"
    # Validate: must be HTTPS and *.supabase.co
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("Supabase URL must use HTTPS.")
    if not parsed.netloc.endswith(".supabase.co"):
        raise ValueError(
            "URL must be a Supabase endpoint (*.supabase.co)."
        )
    return url


# --------------------------------------------------------------------------- #
# Client
# --------------------------------------------------------------------------- #


class OpenBrainClient:
    """Async client for the Open Brain backend (Supabase + OpenRouter)."""

    def __init__(self, config: dict):
        self.config = config or {}
        self._session: aiohttp.ClientSession | None = None

        sec = self.config.get("security") or {}
        self.timeout = aiohttp.ClientTimeout(total=float(sec.get("http_timeout", 30)))
        self.max_thought_length = int(sec.get("max_thought_length", 8000))
        self.max_arg_length = int(sec.get("max_arg_length", 2000))
        defaults = self.config.get("defaults") or {}
        self.default_limit = int(defaults.get("result_limit", 10))
        self.default_threshold = float(defaults.get("match_threshold", 0.5))

        source_cfg = self.config.get("source") or {}
        self.default_source = source_cfg.get("default") or "agent_zero"

        openrouter = self.config.get("openrouter") or {}
        self.embedding_model = openrouter.get("embedding_model") or DEFAULT_EMBEDDING_MODEL
        self.extraction_model = openrouter.get("extraction_model") or DEFAULT_EXTRACTION_MODEL
        self._openrouter_key = openrouter.get("api_key") or ""

        supabase = self.config.get("supabase") or {}
        self._supabase_url = _safe_supabase_url(supabase.get("url") or "")
        self._supabase_key = supabase.get("secret_key") or ""

    # ---- factory ---------------------------------------------------------- #

    @classmethod
    def from_config(cls, agent=None) -> "OpenBrainClient":
        return cls(get_open_brain_config(agent))

    # ---- lifecycle -------------------------------------------------------- #

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None

    async def __aenter__(self) -> "OpenBrainClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    # ---- header helpers --------------------------------------------------- #

    def _supabase_headers(self) -> dict:
        return {
            "apikey": self._supabase_key,
            "Authorization": f"Bearer {self._supabase_key}",
            "Content-Type": "application/json",
        }

    def _openrouter_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._openrouter_key}",
            "Content-Type": "application/json",
        }

    def _rpc_url(self, fn_name: str) -> str:
        return f"{self._supabase_url}/rest/v1/rpc/{fn_name}"

    def _rest_url(self, path: str) -> str:
        return f"{self._supabase_url}/rest/v1/{path}"

    # ---- OpenRouter ------------------------------------------------------- #

    async def get_embedding(self, text: str) -> tuple[bool, Any]:
        """Fetch an embedding vector for `text` via OpenRouter.

        Returns (True, list[float]) or (False, error_string).
        """
        if not text:
            return False, "Embedding input is empty."
        session = await self._get_session()
        try:
            async with session.post(
                f"{OPENROUTER_BASE}/embeddings",
                headers=self._openrouter_headers(),
                json={"model": self.embedding_model, "input": text},
            ) as resp:
                if resp.status != 200:
                    logger.warning("OpenRouter embeddings failed: %s", resp.status)
                    return False, f"Embedding request failed (HTTP {resp.status})."
                data = await resp.json()
                try:
                    return True, data["data"][0]["embedding"]
                except (KeyError, IndexError, TypeError):
                    return False, "Embedding response was malformed."
        except aiohttp.ClientError as e:
            logger.warning("OpenRouter embeddings network error: %s", type(e).__name__)
            return False, "Embedding request failed: network error."
        except Exception as e:
            logger.warning("OpenRouter embeddings unexpected error: %s", type(e).__name__)
            return False, "Embedding request failed."

    async def extract_metadata(self, text: str) -> dict:
        """Extract structured metadata from `text` via OpenRouter.

        Matches the OB1 canonical metadata schema. Always returns a dict —
        on failure it returns a safe fallback so capture still proceeds.
        """
        if not text:
            return {"topics": ["uncategorized"], "type": "observation"}
        session = await self._get_session()
        body = {
            "model": self.extraction_model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": _METADATA_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        }
        try:
            async with session.post(
                f"{OPENROUTER_BASE}/chat/completions",
                headers=self._openrouter_headers(),
                json=body,
            ) as resp:
                if resp.status != 200:
                    logger.warning("Metadata extraction HTTP %s", resp.status)
                    return {"topics": ["uncategorized"], "type": "observation"}
                data = await resp.json()
                try:
                    content = data["choices"][0]["message"]["content"]
                    parsed = json.loads(content)
                    if not isinstance(parsed, dict):
                        raise ValueError("Not a dict")
                    # Normalize — make sure required fields exist
                    parsed.setdefault("topics", ["uncategorized"])
                    parsed.setdefault("type", "observation")
                    return parsed
                except (KeyError, IndexError, ValueError, json.JSONDecodeError):
                    return {"topics": ["uncategorized"], "type": "observation"}
        except Exception as e:
            logger.warning("Metadata extraction failed: %s", type(e).__name__)
            return {"topics": ["uncategorized"], "type": "observation"}

    # ---- Capture ---------------------------------------------------------- #

    async def capture_thought(
        self,
        content: str,
        source: str | None = None,
        extra_metadata: dict | None = None,
    ) -> tuple[bool, dict | str]:
        """Capture a thought to Open Brain.

        Matches the upstream MCP server pattern: direct INSERT with the
        embedding inline. If the optional upsert_thought RPC is available
        (OB1 step 2.6), it will be used for content-fingerprint dedup;
        otherwise falls back to direct INSERT (same as the MCP server).

        Returns (True, {"id": ..., "metadata": ..., "source": ...}) or
        (False, error_string).
        """
        if not content or not content.strip():
            return False, "Cannot capture an empty thought."

        source_tag = source or self.default_source
        extra = extra_metadata or {}

        # 1. Embedding + metadata extraction
        ok_emb, emb_or_err = await self.get_embedding(content)
        if not ok_emb:
            return False, emb_or_err

        metadata = await self.extract_metadata(content)
        metadata["source"] = source_tag
        for k, v in extra.items():
            metadata.setdefault(k, v)

        session = await self._get_session()

        # 2. Try upsert_thought RPC first (dedup). If the RPC is not
        #    installed (404), fall back to direct INSERT — same as the
        #    upstream MCP server.
        thought_id = None
        used_upsert = False

        try:
            async with session.post(
                self._rpc_url("upsert_thought"),
                headers=self._supabase_headers(),
                json={
                    "p_content": content,
                    "p_payload": {"metadata": metadata},
                },
            ) as resp:
                if resp.status in (200, 201):
                    upsert_result = await resp.json()
                    if isinstance(upsert_result, dict):
                        thought_id = upsert_result.get("id")
                    elif isinstance(upsert_result, list) and upsert_result:
                        first = upsert_result[0]
                        if isinstance(first, dict):
                            thought_id = first.get("id")
                    if thought_id:
                        used_upsert = True
                elif resp.status != 404:
                    # Non-404 error from the RPC — still fall through to INSERT
                    logger.warning("upsert_thought returned %s, falling back to INSERT", resp.status)
                # 404 → RPC not installed, fall through silently
        except Exception:
            logger.debug("upsert_thought RPC unavailable, using direct INSERT")

        # 2b. If upsert_thought wrote the row, patch the embedding onto it
        if used_upsert and thought_id:
            try:
                url = self._rest_url("thoughts") + f"?id=eq.{thought_id}"
                async with session.patch(
                    url,
                    headers={**self._supabase_headers(), "Prefer": "return=minimal"},
                    json={"embedding": emb_or_err},
                ) as resp:
                    if resp.status not in (200, 204):
                        logger.warning("embedding patch failed: %s", resp.status)
                        return False, "Thought saved but embedding update failed."
            except Exception:
                return False, "Thought saved but embedding update failed."

            return True, {
                "id": thought_id,
                "metadata": metadata,
                "source": source_tag,
            }

        # 3. Fallback: direct INSERT (matches MCP server pattern exactly)
        try:
            async with session.post(
                self._rest_url("thoughts"),
                headers={
                    **self._supabase_headers(),
                    "Prefer": "return=representation",
                },
                json={
                    "content": content,
                    "embedding": emb_or_err,
                    "metadata": metadata,
                },
            ) as resp:
                if resp.status not in (200, 201):
                    body = await resp.text()
                    logger.warning("INSERT thoughts failed: %s %s", resp.status, body[:200])
                    return False, f"Capture failed (HTTP {resp.status})."
                insert_result = await resp.json()
        except aiohttp.ClientError:
            return False, "Capture failed: network error."
        except Exception:
            return False, "Capture failed."

        # Extract ID from the returned row
        if isinstance(insert_result, list) and insert_result:
            thought_id = insert_result[0].get("id")
        elif isinstance(insert_result, dict):
            thought_id = insert_result.get("id")

        return True, {
            "id": thought_id,
            "metadata": metadata,
            "source": source_tag,
        }

    # ---- Search ----------------------------------------------------------- #

    async def search_thoughts(
        self,
        query: str,
        limit: int | None = None,
        threshold: float | None = None,
        source: str | None = None,
        extra_filter: dict | None = None,
    ) -> tuple[bool, list | str]:
        """Semantic search via the match_thoughts RPC.

        `source` and `extra_filter` build a metadata `@>` filter that is
        pushed into the RPC. Aligns with OB1 recipes/source-filtering.
        """
        query = (query or "").strip()
        if not query:
            return False, "Search query is empty."

        ok_emb, emb_or_err = await self.get_embedding(query)
        if not ok_emb:
            return False, emb_or_err

        filter_obj: dict = {}
        if source:
            filter_obj["source"] = source
        if extra_filter:
            filter_obj.update(extra_filter)

        session = await self._get_session()
        try:
            async with session.post(
                self._rpc_url("match_thoughts"),
                headers=self._supabase_headers(),
                json={
                    "query_embedding": emb_or_err,
                    "match_threshold": float(threshold if threshold is not None else self.default_threshold),
                    "match_count": int(limit or self.default_limit),
                    "filter": filter_obj,
                },
            ) as resp:
                if resp.status != 200:
                    logger.warning("match_thoughts failed: %s", resp.status)
                    if resp.status == 404:
                        return False, "match_thoughts RPC not found. Complete OB1 setup step 2.3."
                    return False, f"Search failed (HTTP {resp.status})."
                data = await resp.json()
                if not isinstance(data, list):
                    return False, "Search response was malformed."
                return True, data
        except aiohttp.ClientError:
            return False, "Search failed: network error."
        except Exception:
            return False, "Search failed."

    # ---- List ------------------------------------------------------------- #

    async def list_thoughts(
        self,
        limit: int | None = None,
        thought_type: str | None = None,
        topic: str | None = None,
        person: str | None = None,
        source: str | None = None,
        days: int | None = None,
    ) -> tuple[bool, list | str]:
        """List recent thoughts with optional metadata filters.

        Mirrors OB1 list_thoughts: filters are applied via Supabase's
        `metadata @>` operator (encoded as `cs.` in PostgREST).
        """
        session = await self._get_session()

        params: list[tuple[str, str]] = [
            ("select", "id,content,metadata,created_at"),
            ("order", "created_at.desc"),
            ("limit", str(int(limit or self.default_limit))),
        ]

        # Build cumulative metadata containment filter. PostgREST supports
        # chained metadata=cs.{...} but each extra filter replaces the last,
        # so we merge into a single JSON blob.
        meta_filter: dict = {}
        if thought_type:
            meta_filter["type"] = thought_type
        if source:
            meta_filter["source"] = source
        if topic:
            meta_filter["topics"] = [topic]
        if person:
            meta_filter["people"] = [person]
        if meta_filter:
            params.append(("metadata", "cs." + json.dumps(meta_filter)))

        if days and days > 0:
            # PostgREST timestamp filter
            from datetime import datetime, timedelta, timezone

            since = (datetime.now(tz=timezone.utc) - timedelta(days=int(days))).isoformat()
            params.append(("created_at", f"gte.{since}"))

        try:
            async with session.get(
                self._rest_url("thoughts"),
                headers=self._supabase_headers(),
                params=params,
            ) as resp:
                if resp.status != 200:
                    logger.warning("list_thoughts failed: %s", resp.status)
                    return False, f"List failed (HTTP {resp.status})."
                data = await resp.json()
                if not isinstance(data, list):
                    return False, "List response was malformed."
                return True, data
        except aiohttp.ClientError:
            return False, "List failed: network error."
        except Exception:
            return False, "List failed."

    # ---- Stats ------------------------------------------------------------ #

    async def thought_stats(self, source: str | None = None) -> tuple[bool, dict | str]:
        """Compute summary stats client-side over recent rows.

        OB1's canonical implementation also does client-side aggregation —
        there's no dedicated aggregate RPC. We cap rows to keep it bounded.
        """
        session = await self._get_session()

        params: list[tuple[str, str]] = [
            ("select", "metadata,created_at"),
            ("order", "created_at.desc"),
            ("limit", "1000"),
        ]
        if source:
            params.append(("metadata", "cs." + json.dumps({"source": source})))

        try:
            async with session.get(
                self._rest_url("thoughts"),
                headers=self._supabase_headers(),
                params=params,
            ) as resp:
                if resp.status != 200:
                    return False, f"Stats failed (HTTP {resp.status})."
                rows = await resp.json()
                if not isinstance(rows, list):
                    return False, "Stats response was malformed."
        except aiohttp.ClientError:
            return False, "Stats failed: network error."
        except Exception:
            return False, "Stats failed."

        types: dict[str, int] = {}
        topics: dict[str, int] = {}
        people: dict[str, int] = {}
        sources: dict[str, int] = {}

        for r in rows:
            meta = (r.get("metadata") or {}) if isinstance(r, dict) else {}
            t = meta.get("type")
            if t:
                types[t] = types.get(t, 0) + 1
            s = meta.get("source")
            if s:
                sources[s] = sources.get(s, 0) + 1
            for tag in meta.get("topics") or []:
                topics[tag] = topics.get(tag, 0) + 1
            for p in meta.get("people") or []:
                people[p] = people.get(p, 0) + 1

        def top(d: dict[str, int], n: int = 10) -> list[tuple[str, int]]:
            return sorted(d.items(), key=lambda kv: kv[1], reverse=True)[:n]

        oldest = rows[-1].get("created_at") if rows else None
        newest = rows[0].get("created_at") if rows else None

        return True, {
            "sample_size": len(rows),
            "oldest": oldest,
            "newest": newest,
            "types": dict(top(types)),
            "topics": dict(top(topics)),
            "people": dict(top(people)),
            "sources": dict(top(sources)),
        }

    # ---- Connection test -------------------------------------------------- #

    async def ping(self) -> tuple[bool, dict | str]:
        """Lightweight health check.

        Hits the thoughts table with `limit=1` — verifies Supabase URL,
        secret key, table existence, and service_role grants all in one
        round trip. Does NOT touch OpenRouter.
        """
        session = await self._get_session()
        try:
            async with session.get(
                self._rest_url("thoughts"),
                headers=self._supabase_headers(),
                params=[("select", "id"), ("limit", "1")],
            ) as resp:
                if resp.status == 401:
                    return False, "Supabase auth failed: secret key invalid."
                if resp.status == 404:
                    return False, "thoughts table not found. Run OB1 setup step 2.2."
                if resp.status != 200:
                    return False, f"Supabase ping failed (HTTP {resp.status})."
                return True, {"supabase": "ok"}
        except aiohttp.ClientError:
            return False, "Supabase unreachable: network error."
        except Exception:
            return False, "Supabase unreachable."
