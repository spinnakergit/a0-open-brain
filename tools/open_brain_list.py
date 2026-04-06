"""Open Brain — list recent thoughts with metadata filters."""

from helpers.tool import Tool, Response


class OpenBrainList(Tool):
    """List recent thoughts with optional type/topic/person/source/days filters."""

    async def execute(self, **kwargs) -> Response:
        thought_type = (self.args.get("type") or "").strip() or None
        topic = (self.args.get("topic") or "").strip() or None
        person = (self.args.get("person") or "").strip() or None
        source_arg = (self.args.get("source") or "").strip() or None

        try:
            limit = int(self.args.get("limit") or 0) or None
        except (TypeError, ValueError):
            limit = None
        try:
            days = int(self.args.get("days") or 0) or None
        except (TypeError, ValueError):
            days = None

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

        if thought_type:
            thought_type = sanitize_arg(thought_type, 64)
        if topic:
            topic = sanitize_arg(topic, 128)
        if person:
            person = sanitize_arg(person, 128)

        source = None
        if source_arg:
            try:
                source = validate_source_tag(sanitize_arg(source_arg, 64))
            except ValueError as e:
                return Response(message=f"Error: {e}", break_loop=False)

        if limit is not None:
            limit = max(1, min(int(limit), 50))
        if days is not None:
            days = max(1, min(int(days), 365))

        client = OpenBrainClient(config)
        try:
            ok, result = await client.list_thoughts(
                limit=limit,
                thought_type=thought_type,
                topic=topic,
                person=person,
                source=source,
                days=days,
            )
        finally:
            await client.close()

        if not ok:
            return Response(message=f"Open Brain: {result}", break_loop=False)

        if not result:
            return Response(message="No thoughts found matching those filters.", break_loop=False)

        filter_bits = []
        if thought_type:
            filter_bits.append(f"type={thought_type}")
        if source:
            filter_bits.append(f"source={source}")
        if topic:
            filter_bits.append(f"topic={topic}")
        if person:
            filter_bits.append(f"person={person}")
        if days:
            filter_bits.append(f"last {days}d")
        header = f"{len(result)} recent thought(s)"
        if filter_bits:
            header += " (" + ", ".join(filter_bits) + ")"

        lines = [header, ""]
        for i, t in enumerate(result, start=1):
            lines.append(format_retrieved_thought(t, index=i))
            lines.append("")
        return Response(message="\n".join(lines).rstrip(), break_loop=False)
