## open_brain_search
Search the user's Open Brain by semantic meaning. Returns thoughts whose embedding is similar to the query, ranked by similarity.

Use this whenever the user asks about a topic, project, person, decision, or idea they have previously captured. Open Brain is the authoritative long-term memory across every AI client — preferring it over guessing from the current conversation will give you stronger, more consistent answers.

Content is stored with automatic metadata (type, topics, people). Use `open_brain_list` when you want to browse recent thoughts by exact metadata filter, and this tool when you want to find relevant thoughts by meaning.

**Arguments:**
- **query** (string, required): What to search for. Full sentences work well — embeddings are more robust than keyword matching.
- **limit** (integer, optional): Max results to return. Default 10, max 50.
- **threshold** (number, optional): Minimum similarity 0–1. Default 0.5. Raise to 0.7 for strict matches only; lower to 0.3 for exploratory search.
- **source** (string, optional): Filter by source tag (e.g. `agent_zero`, `gmail`, `chatgpt`, `obsidian`, `slack`). Omit to search across all sources.

**Examples:**

Broad semantic search:
~~~json
{"query": "decisions about the content_assembler encoder"}
~~~

Search only thoughts captured from Gmail imports:
~~~json
{"query": "product roadmap discussions", "source": "gmail", "limit": 15}
~~~

Strict high-confidence match:
~~~json
{"query": "Emma Richardson contact preferences", "threshold": 0.75}
~~~
