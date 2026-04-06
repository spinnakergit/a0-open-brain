## open_brain_recall
High-signal recall tool designed for agent workflows. Searches Open Brain, filters to confident hits only, and returns a compact bulleted list ready to inject into your next turn.

Use this at the start of a session, or when the user introduces a new person, project, or topic. Prefer this over `open_brain_search` when you are trying to proactively surface context rather than answer a direct search query. Stay quiet if nothing confident comes back — the tool returns a short "no hits" message which you should usually suppress (do not mention the failed recall to the user).

This is the read side of the Open Brain flywheel. The write side is `open_brain_capture`.

**Arguments:**
- **query** (string, required): The topic, person, project, or question to recall against. Short phrases work well.
- **limit** (integer, optional): Max results. Default 10, max 25.
- **min_score** (number, optional): Minimum similarity 0–1 for a hit to surface. Default 0.6 (OB1 canonical recall threshold).
- **sources** (string, optional): Comma-separated source tags to fan out across (e.g. `agent_zero,gmail,slack`). Omit to search all sources.

**Examples:**

Recall on a person at session start:
~~~json
{"query": "Emma Richardson"}
~~~

Recall on a project topic with high confidence:
~~~json
{"query": "content_assembler encoder decisions", "min_score": 0.7}
~~~

Fan out across multiple sources:
~~~json
{"query": "pricing feedback", "sources": "gmail,slack,chatgpt"}
~~~
