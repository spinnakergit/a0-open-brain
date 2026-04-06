"""Open Brain — semantic search.

Finds thoughts by meaning using the upstream match_thoughts RPC.
Supports source filtering per OB1 recipes/source-filtering.
"""

from helpers.tool import Tool, Response


class OpenBrainSearch(Tool):
    """Search Open Brain by semantic similarity."""

    async def execute(self, **kwargs) -> Response:
        query = (self.args.get("query") or "").strip()
        source_arg = (self.args.get("source") or "").strip() or None

        try:
            limit = int(self.args.get("limit") or 0) or None
        except (TypeError, ValueError):
            limit = None
        try:
            threshold = float(self.args.get("threshold") or 0) or None
        except (TypeError, ValueError):
            threshold = None

        if not query:
            return Response(
                message="Error: 'query' is required. Describe what to search for.",
                break_loop=False,
            )

        from usr.plugins.open_brain.helpers.open_brain_client import (
            OpenBrainClient,
            get_open_brain_config,
            is_configured,
        )
        from usr.plugins.open_brain.helpers.sanitize import (
            sanitize_arg,
            validate_source_tag,
            format_retrieved_thought,
        )

        config = get_open_brain_config(self.agent)
        ok, reason = is_configured(config)
        if not ok:
            return Response(message=f"Error: {reason}", break_loop=False)

        sec = config.get("security") or {}
        query = sanitize_arg(query, int(sec.get("max_arg_length", 2000)))

        source = None
        if source_arg:
            try:
                source = validate_source_tag(sanitize_arg(source_arg, 64))
            except ValueError as e:
                return Response(message=f"Error: {e}", break_loop=False)

        if limit is not None:
            limit = max(1, min(int(limit), 50))
        if threshold is not None:
            threshold = max(0.0, min(float(threshold), 1.0))

        client = OpenBrainClient(config)
        try:
            ok, result = await client.search_thoughts(
                query=query,
                limit=limit,
                threshold=threshold,
                source=source,
            )
        finally:
            await client.close()

        if not ok:
            return Response(message=f"Open Brain: {result}", break_loop=False)

        if not result:
            hint = f' (source={source})' if source else ''
            return Response(
                message=f"No thoughts found matching: {query}{hint}",
                break_loop=False,
            )

        lines = [f"Found {len(result)} thought(s) matching: {query}"]
        if source:
            lines[0] += f" (source={source})"
        lines.append("")
        for i, t in enumerate(result, start=1):
            lines.append(format_retrieved_thought(t, index=i))
            lines.append("")
        return Response(message="\n".join(lines).rstrip(), break_loop=False)
