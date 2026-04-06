"""Open Brain — summary statistics."""

from helpers.tool import Tool, Response


class OpenBrainStats(Tool):
    """Summary stats across captured thoughts.

    Returns counts by type, top topics, top people, source breakdown, and
    date range. Scoped to a single source via the `source` parameter.
    """

    async def execute(self, **kwargs) -> Response:
        source_arg = (self.args.get("source") or "").strip() or None

        from usr.plugins.open_brain.helpers.open_brain_client import (
            OpenBrainClient,
            get_open_brain_config,
            is_configured,
        )
        from usr.plugins.open_brain.helpers.sanitize import (
            sanitize_arg,
            validate_source_tag,
        )

        config = get_open_brain_config(self.agent)
        ok, reason = is_configured(config)
        if not ok:
            return Response(message=f"Error: {reason}", break_loop=False)

        source = None
        if source_arg:
            try:
                source = validate_source_tag(sanitize_arg(source_arg, 64))
            except ValueError as e:
                return Response(message=f"Error: {e}", break_loop=False)

        client = OpenBrainClient(config)
        try:
            ok, result = await client.thought_stats(source=source)
        finally:
            await client.close()

        if not ok:
            return Response(message=f"Open Brain: {result}", break_loop=False)

        lines: list[str] = []
        header = f"Open Brain stats — sample size: {result.get('sample_size', 0)}"
        if source:
            header += f" (source={source})"
        lines.append(header)

        oldest = result.get("oldest") or "n/a"
        newest = result.get("newest") or "n/a"
        lines.append(f"Date range: {oldest[:10] if oldest != 'n/a' else oldest} → {newest[:10] if newest != 'n/a' else newest}")

        def render_section(title: str, d: dict) -> None:
            if not d:
                return
            lines.append("")
            lines.append(f"{title}:")
            for k, v in d.items():
                lines.append(f"  {k}: {v}")

        render_section("Types", result.get("types") or {})
        render_section("Top topics", result.get("topics") or {})
        render_section("People mentioned", result.get("people") or {})
        if not source:
            render_section("By source", result.get("sources") or {})

        return Response(message="\n".join(lines), break_loop=False)
