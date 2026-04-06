## open_brain_digest
Produce a human-readable summary of recent Open Brain activity: totals, type breakdown, top topics, top people, source mix, open action items, and highlight thoughts.

Use this for "what happened yesterday?", "give me a brain digest for this week", or at the start of a work session to orient yourself on what the user has been thinking about. This is deterministic — no LLM call — so it is cheap and safe to run often.

For an LLM-narrated digest, take the output of this tool and pass it to the agent's reasoning step.

**Arguments:**
- **days** (integer, optional): Window size in days. Default 1, max 90.
- **limit** (integer, optional): Max thoughts to analyze. Default 50, max 200.
- **type** (string, optional): Restrict to a single thought type (`observation`, `task`, `idea`, `reference`, `person_note`).
- **source** (string, optional): Restrict to a single source tag.

**Examples:**

Today's digest:
~~~json
{}
~~~

Weekly digest of just tasks:
~~~json
{"days": 7, "type": "task"}
~~~

Monthly digest from Gmail imports only:
~~~json
{"days": 30, "source": "gmail", "limit": 200}
~~~
