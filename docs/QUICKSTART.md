# Open Brain Plugin — Quick Start

Get from zero to your first capture + first semantic recall in about five minutes.

## Prerequisites

- A running Agent Zero instance (Docker or local)
- A working **Open Brain (OB1)** Supabase project — specifically:
  - The `thoughts` table (OB1 setup step 2.2)
  - The `match_thoughts(query_embedding, match_threshold, match_count, filter)` RPC (setup step 2.3)
  - Optional: the `upsert_thought(p_content, p_payload)` RPC for fingerprint dedup (setup step 2.6). Without it, captures use direct INSERT — same as the MCP server.
- An [OpenRouter](https://openrouter.ai) API key with access to `text-embedding-3-small`

If you do not yet have an OB1 project, follow
[OB1 docs/01-getting-started.md](https://github.com/NateBJones-Projects/OB1/blob/main/docs/01-getting-started.md)
first. The full setup takes ~30 minutes and gives you the exact same database
that Claude Desktop, ChatGPT, and every other MCP client will share with Agent
Zero through this plugin.

## 1. Install the plugin

From inside the Agent Zero container (or local A0 install):

```bash
cd /path/to/a0-open-brain
./install.sh
```

This copies the plugin into `/a0/usr/plugins/open_brain/` and enables it via
the `.toggle-1` marker. Restart the container — or click *Init* on the plugin
card in the WebUI — to pick up new dependencies.

## 2. Configure credentials

1. Open the Agent Zero WebUI.
2. Go to **Settings → External Services → Open Brain**.
3. Open the **Credentials** tab and paste:
   - **Supabase Project URL** — e.g. `https://xxxxxxxx.supabase.co`
   - **Supabase Secret Key** — the `service_role` key (OR a scoped secret key with grants on `thoughts` and `match_thoughts`)
   - **OpenRouter API Key** — starts with `sk-or-`
4. Close the settings panel. Agent Zero writes a 0600 `config.json` under
   `/a0/usr/plugins/open_brain/` with the new values.

> Secrets are **never** returned in cleartext after they are saved. The next
> time you open the panel they appear as `AA****ZZ` — editing that masked value
> deliberately preserves the original secret.

## 3. Verify the connection

Open the Open Brain **Dashboard** (same plugin card, *Main* view) and click
**Test Connection**. You should see:

```
OK — 1 thought(s) reachable
```

If you see an error, see [SETUP.md](SETUP.md#troubleshooting).

## 4. Capture your first thought

Ask the agent to capture something:

> "Open Brain: remember that our Q2 launch window is the second week of April
> and the blocker is the legal review on the privacy policy."

The agent will call `open_brain_capture` with:

```json
{
  "content": "Q2 launch window is the second week of April. Blocker: legal review on the privacy policy."
}
```

Behind the scenes the plugin:

1. Sanitizes the content (strips any injection patterns, caps length).
2. Extracts metadata with `gpt-4o-mini` — `type: task`, `topics: [q2-launch]`,
   `people: []`, `action_items: [...]`, `dates_mentioned: [...]`.
3. Generates an embedding via OpenRouter (`text-embedding-3-small`).
4. Inserts the thought directly into the `thoughts` table with content,
   embedding, and metadata in one call — matching the upstream MCP server
   pattern. If the optional `upsert_thought` RPC is installed, it is used
   automatically for content-fingerprint dedup.

You should see a confirmation like:

```
Captured thought (id=42). type=task, topics=[q2-launch], source=agent_zero.
```

## 5. Search what you just captured

From a fresh session (or even another A0 container — the data lives in
Supabase, not the plugin), ask:

> "What do we know about the Q2 launch?"

The agent will call `open_brain_search` and get back a ranked list of
matching thoughts, each with its capture date, type, topics, and a compact
content preview. Because the same Supabase table is shared with every OB1
client, the same query in Claude Desktop or ChatGPT will return the same
result.

## 6. Try recall and digest

- **Recall** (agent-tuned): `open_brain_recall` with a stricter threshold and
  multi-source fan-out — use when the agent needs high-signal context during a
  task, not a full search.
- **Digest**: `open_brain_digest` returns a deterministic report of activity
  over a window (defaults to 7 days) — totals, types, top topics, top people,
  open action items, highlights. Ask "give me a digest of this week" to see
  it.

## What next?

- Read [SETUP.md](SETUP.md) for the full credential setup walkthrough and
  troubleshooting.
- Read [DEVELOPMENT.md](DEVELOPMENT.md) if you want to extend the plugin or
  add new tools.
- Read the upstream OB1 recipes
  ([source-filtering](https://github.com/NateBJones-Projects/OB1/tree/main/recipes/source-filtering),
  [live-retrieval](https://github.com/NateBJones-Projects/OB1/tree/main/recipes/live-retrieval),
  [daily-digest](https://github.com/NateBJones-Projects/OB1/tree/main/recipes/daily-digest))
  to see what else you can do with the same data from other AI clients.
