## open_brain_capture
Save a thought to the user's Open Brain — their unified semantic memory shared across every AI client (Claude Desktop, ChatGPT, Claude Code, other Agent Zero instances, etc.).

Use this tool when you have something worth remembering across sessions and platforms: decisions, ACT NOW items, observations about people, references, ideas worth preserving, or session summaries. Do NOT use it for ephemeral task state or raw conversation transcripts — Open Brain is long-term, high-signal memory.

Captured thoughts are automatically embedded and tagged (type, topics, people, action items, dates). Content-fingerprint deduplication means capturing the same thought twice merges metadata instead of creating duplicates — so it is safe to re-capture when unsure.

**Arguments:**
- **content** (string, required): The thought to capture. Write it as a clear, standalone statement that will make sense months later when retrieved by any AI client. Include why it matters, not just what it is.
- **source** (string, optional): Source tag for filtering later. Defaults to `agent_zero`. Only override when the thought actually originates from a different context (e.g., `gmail` when capturing on behalf of an inbox import).

**Examples:**

Capture an ACT NOW decision:
~~~json
{"content": "ACT NOW: switch the content_assembler encoder to two-pass x264 for thumbnails. Single-pass causes 20% file bloat on silent sections. Verified 2026-04-02."}
~~~

Capture a person note:
~~~json
{"content": "Emma Richardson (Vercel DX team) is the right contact for edge-function cold-start questions. Prefers short async DMs, not calls."}
~~~

Capture a session summary:
~~~json
{"content": "Session summary: spent 90 minutes on the Open Brain plugin. Decided to direct-call Supabase+OpenRouter instead of implementing MCP client. Matches upstream MCP server capture pattern. 6 tools, 3 skills. Next: regression suite."}
~~~
