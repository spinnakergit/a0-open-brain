"""Open Brain — capture a thought.

Writes a new thought to the user's unified semantic memory. Matches the
upstream MCP server capture pattern (direct INSERT). If the optional
upsert_thought RPC is installed, it is used automatically for dedup.
"""

from helpers.tool import Tool, Response


class OpenBrainCapture(Tool):
    """Save a thought to Open Brain."""

    async def execute(self, **kwargs) -> Response:
        content = (self.args.get("content") or "").strip()
        source_arg = (self.args.get("source") or "").strip() or None

        if not content:
            return Response(
                message="Error: 'content' is required. Provide the thought to capture.",
                break_loop=False,
            )

        from usr.plugins.open_brain.helpers.open_brain_client import (
            OpenBrainClient,
            get_open_brain_config,
            is_configured,
        )
        from usr.plugins.open_brain.helpers.sanitize import (
            sanitize_thought_content,
            sanitize_arg,
            validate_source_tag,
        )

        config = get_open_brain_config(self.agent)
        ok, reason = is_configured(config)
        if not ok:
            return Response(message=f"Error: {reason}", break_loop=False)

        sec = config.get("security") or {}
        max_len = int(sec.get("max_thought_length", 8000))
        content = sanitize_thought_content(content, max_length=max_len)

        if not content:
            return Response(
                message="Error: content was empty after sanitization.",
                break_loop=False,
            )

        source = None
        if source_arg:
            try:
                source = validate_source_tag(sanitize_arg(source_arg, 64))
            except ValueError as e:
                return Response(message=f"Error: {e}", break_loop=False)

        client = OpenBrainClient(config)
        try:
            ok, result = await client.capture_thought(content=content, source=source)
        finally:
            await client.close()

        if not ok:
            return Response(message=f"Open Brain: {result}", break_loop=False)

        meta = result.get("metadata") or {}
        parts = [f"Captured to Open Brain as {meta.get('type', 'thought')}"]
        topics = meta.get("topics") or []
        people = meta.get("people") or []
        actions = meta.get("action_items") or []
        src = result.get("source")
        if topics:
            parts.append(f"topics: {', '.join(str(t) for t in topics)}")
        if people:
            parts.append(f"people: {', '.join(str(p) for p in people)}")
        if actions:
            parts.append(f"actions: {'; '.join(str(a) for a in actions)}")
        if src:
            parts.append(f"source: {src}")
        return Response(message=" | ".join(parts), break_loop=False)
