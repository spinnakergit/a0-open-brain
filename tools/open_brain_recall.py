"""Open Brain — recall.

A higher-level retrieval tool. Where `open_brain_search` is raw semantic
search, `recall` is purpose-built for agent workflows:

  - multi-term fan-out (query can be a sentence or a list of topics)
  - automatic source scoping to agent_zero + any extra sources
  - score-threshold filtering so the agent only sees confident hits
  - compact output tuned for injection into the agent's next turn

Mirrors the "read side" of the OB1 flywheel captured by the live-retrieval
skill (recipes/live-retrieval).
"""

from helpers.tool import Tool, Response


class OpenBrainRecall(Tool):
    """Recall relevant thoughts for the current conversation context."""

    async def execute(self, **kwargs) -> Response:
        query = (self.args.get("query") or "").strip()
        sources_arg = (self.args.get("sources") or "").strip()

        try:
            limit = int(self.args.get("limit") or 0) or None
        except (TypeError, ValueError):
            limit = None
        try:
            min_score = float(self.args.get("min_score") or 0) or None
        except (TypeError, ValueError):
            min_score = None

        if not query:
            return Response(
                message="Error: 'query' is required. Provide the topic, person, or context to recall against.",
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
        )

        config = get_open_brain_config(self.agent)
        ok, reason = is_configured(config)
        if not ok:
            return Response(message=f"Error: {reason}", break_loop=False)

        defaults = config.get("defaults") or {}
        recall_threshold = float(
            min_score if min_score is not None else defaults.get("recall_score_threshold", 0.6)
        )
        recall_limit = int(limit if limit else defaults.get("result_limit", 10))
        recall_limit = max(1, min(recall_limit, 25))

        sec = config.get("security") or {}
        query = sanitize_arg(query, int(sec.get("max_arg_length", 2000)))

        # Parse sources (comma separated). If empty, search across all sources.
        source_list: list[str] = []
        if sources_arg:
            for raw in sources_arg.split(","):
                s = raw.strip().lower()
                if not s:
                    continue
                try:
                    source_list.append(validate_source_tag(sanitize_arg(s, 64)))
                except ValueError as e:
                    return Response(message=f"Error: {e}", break_loop=False)

        client = OpenBrainClient(config)
        try:
            # Search lower than the display threshold and then filter client-side,
            # so we can deduplicate across source fan-outs.
            search_threshold = max(0.0, recall_threshold - 0.1)
            aggregated: dict[str, dict] = {}

            if source_list:
                for src in source_list:
                    ok, hits = await client.search_thoughts(
                        query=query,
                        limit=recall_limit,
                        threshold=search_threshold,
                        source=src,
                    )
                    if not ok:
                        return Response(message=f"Open Brain: {hits}", break_loop=False)
                    for h in hits:
                        tid = h.get("id") or h.get("content")
                        if tid and tid not in aggregated:
                            aggregated[tid] = h
            else:
                ok, hits = await client.search_thoughts(
                    query=query,
                    limit=recall_limit,
                    threshold=search_threshold,
                )
                if not ok:
                    return Response(message=f"Open Brain: {hits}", break_loop=False)
                for h in hits:
                    tid = h.get("id") or h.get("content")
                    if tid and tid not in aggregated:
                        aggregated[tid] = h
        finally:
            await client.close()

        # Apply display threshold and rank by similarity
        filtered = [
            h for h in aggregated.values()
            if float(h.get("similarity") or 0) >= recall_threshold
        ]
        filtered.sort(key=lambda h: float(h.get("similarity") or 0), reverse=True)
        filtered = filtered[:recall_limit]

        if not filtered:
            # Silent-on-miss semantics — agent gets a short note so it knows
            # a recall happened but nothing was found. Skills that use this
            # tool can choose to suppress the output.
            return Response(
                message=f"No Open Brain thoughts passed the {recall_threshold:.2f} recall threshold for: {query}",
                break_loop=False,
            )

        lines = [f"Open Brain recall — {len(filtered)} relevant thought(s) for: {query}"]
        for h in filtered:
            meta = h.get("metadata") or {}
            sim = float(h.get("similarity") or 0)
            created = (h.get("created_at") or "")[:10]
            t_type = meta.get("type") or "thought"
            src = meta.get("source") or "?"
            content = (h.get("content") or "").strip().replace("\n", " ")
            if len(content) > 240:
                content = content[:240].rstrip() + "…"
            lines.append(
                f"- [{created}] ({t_type}, source={src}, score={sim:.2f}) {content}"
            )

        return Response(message="\n".join(lines), break_loop=False)
