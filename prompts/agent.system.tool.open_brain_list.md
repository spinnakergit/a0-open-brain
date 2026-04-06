## open_brain_list
List recent Open Brain thoughts by exact metadata filters (type, topic, person, source, time window). Complements `open_brain_search`, which ranks by meaning.

Use this when the user wants to browse activity rather than find a specific idea: "show me what I captured about Vercel this week", "list my recent tasks", "show all person_notes about Emma".

**Arguments:**
- **limit** (integer, optional): Max results. Default 10, max 50.
- **type** (string, optional): One of `observation`, `task`, `idea`, `reference`, `person_note`.
- **topic** (string, optional): Exact topic tag to filter by (must match a tag actually attached to a thought).
- **person** (string, optional): Exact person name to filter by.
- **source** (string, optional): Source tag (e.g. `agent_zero`, `gmail`, `chatgpt`).
- **days** (integer, optional): Only thoughts from the last N days (1–365).

**Examples:**

Recent tasks across all sources:
~~~json
{"type": "task", "limit": 20}
~~~

Last week's thoughts from Slack:
~~~json
{"source": "slack", "days": 7}
~~~

Person notes about Emma:
~~~json
{"type": "person_note", "person": "Emma Richardson"}
~~~
