"""Open Brain — digest.

Produces a compact, human-readable summary of recent activity: what was
captured, grouped by theme, with top topics, top people, and highlighted
action items. The "end of day briefing" read pattern from OB1
recipes/daily-digest, ported to A0 as an on-demand tool.

No LLM call — the digest is produced deterministically from the metadata
already attached to each thought. Agents that want a narrative summary
can pass the digest text through their own LLM.
"""

from helpers.tool import Tool, Response


class OpenBrainDigest(Tool):
    """Summarize recent Open Brain activity."""

    async def execute(self, **kwargs) -> Response:
        source_arg = (self.args.get("source") or "").strip() or None
        thought_type = (self.args.get("type") or "").strip() or None

        try:
            days = int(self.args.get("days") or 1)
        except (TypeError, ValueError):
            days = 1
        try:
            limit = int(self.args.get("limit") or 50)
        except (TypeError, ValueError):
            limit = 50

        days = max(1, min(days, 90))
        limit = max(5, min(limit, 200))

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
        if thought_type:
            thought_type = sanitize_arg(thought_type, 64)

        client = OpenBrainClient(config)
        try:
            ok, rows = await client.list_thoughts(
                limit=limit,
                thought_type=thought_type,
                source=source,
                days=days,
            )
        finally:
            await client.close()

        if not ok:
            return Response(message=f"Open Brain: {rows}", break_loop=False)

        if not rows:
            return Response(
                message=f"No thoughts captured in the last {days} day(s).",
                break_loop=False,
            )

        # Aggregate
        type_counts: dict[str, int] = {}
        topic_counts: dict[str, int] = {}
        people_counts: dict[str, int] = {}
        source_counts: dict[str, int] = {}
        actions: list[str] = []
        highlights: list[dict] = []

        for r in rows:
            meta = (r.get("metadata") or {}) if isinstance(r, dict) else {}
            t = meta.get("type") or "uncategorized"
            type_counts[t] = type_counts.get(t, 0) + 1
            s = meta.get("source") or "unknown"
            source_counts[s] = source_counts.get(s, 0) + 1
            for tag in meta.get("topics") or []:
                topic_counts[tag] = topic_counts.get(tag, 0) + 1
            for p in meta.get("people") or []:
                people_counts[p] = people_counts.get(p, 0) + 1
            for a in meta.get("action_items") or []:
                if isinstance(a, str) and a.strip():
                    actions.append(a.strip())
            # Highlights: tasks, ideas and references tend to be the
            # high-signal rows. Cap to 5.
            if t in ("task", "idea", "reference") and len(highlights) < 5:
                highlights.append(r)

        def top(d: dict, n: int = 5) -> list[tuple[str, int]]:
            return sorted(d.items(), key=lambda kv: kv[1], reverse=True)[:n]

        lines: list[str] = []
        header = f"Open Brain digest — last {days} day(s)"
        if source:
            header += f" (source={source})"
        if thought_type:
            header += f" (type={thought_type})"
        lines.append(header)
        lines.append(f"Total thoughts: {len(rows)}")

        if type_counts:
            lines.append("")
            lines.append("By type:")
            for k, v in top(type_counts):
                lines.append(f"  {k}: {v}")

        if topic_counts:
            lines.append("")
            lines.append("Top topics:")
            for k, v in top(topic_counts):
                lines.append(f"  {k}: {v}")

        if people_counts:
            lines.append("")
            lines.append("People mentioned:")
            for k, v in top(people_counts):
                lines.append(f"  {k}: {v}")

        if not source and source_counts:
            lines.append("")
            lines.append("By source:")
            for k, v in top(source_counts):
                lines.append(f"  {k}: {v}")

        if actions:
            lines.append("")
            lines.append("Open action items:")
            # Dedup while preserving order, cap to 10
            seen = set()
            shown = 0
            for a in actions:
                key = a.lower()
                if key in seen:
                    continue
                seen.add(key)
                lines.append(f"  - {a}")
                shown += 1
                if shown >= 10:
                    break

        if highlights:
            lines.append("")
            lines.append("Highlights:")
            for h in highlights:
                meta = h.get("metadata") or {}
                created = (h.get("created_at") or "")[:10]
                t = meta.get("type") or "thought"
                content = (h.get("content") or "").strip().replace("\n", " ")
                if len(content) > 200:
                    content = content[:200].rstrip() + "…"
                lines.append(f"  [{created}] ({t}) {content}")

        return Response(message="\n".join(lines), break_loop=False)
