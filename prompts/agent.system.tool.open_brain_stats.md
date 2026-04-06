## open_brain_stats
Get a high-level summary of what is in the user's Open Brain: totals, type distribution, top topics, top people, and source breakdown.

Use this when the user asks "what's in my brain?", "how much have I captured from X?", or when you need a map of the memory landscape before drilling in with `open_brain_search` or `open_brain_list`.

Stats are computed client-side over the 1,000 most recent thoughts (the same pattern the canonical OB1 MCP server uses).

**Arguments:**
- **source** (string, optional): Scope stats to a single source tag. Omit to see the full cross-source picture including a "By source" breakdown.

**Examples:**

Global stats across all sources:
~~~json
{}
~~~

Just my Gmail-sourced thoughts:
~~~json
{"source": "gmail"}
~~~
