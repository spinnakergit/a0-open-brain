# Open Brain Plugin for Agent Zero

**Unified semantic memory for Agent Zero.** Capture, search, recall, and digest
thoughts across every AI client — Claude Desktop, ChatGPT, Claude Code, and any
Agent Zero instance — using the [Open Brain (OB1)](https://github.com/NateBJones-Projects/OB1)
Supabase + pgvector + OpenRouter stack.

One brain. Every AI. No duplicated memory.

## What It Is

Open Brain (OB1) is a personal semantic memory system built on Supabase +
pgvector + OpenRouter, with a remote MCP server so any MCP-capable AI client
can read and write to it. This plugin brings the same memory into Agent Zero
by talking directly to the user's existing OB1 Supabase project — no second
database, no separate memory silo, no MCP client implementation.

If you have already set up OB1 for Claude Desktop (or any other MCP client),
this plugin reuses the exact same three credentials: your Supabase URL, your
Supabase secret key, and your OpenRouter API key.

## Features

- **6 Agent Tools** — `open_brain_capture`, `open_brain_search`,
  `open_brain_list`, `open_brain_stats`, `open_brain_recall`,
  `open_brain_digest`
- **3 Behavioral Skills** aligned with OB1 canonical skills:
  - `open-brain-auto-capture` — saves ACT NOW items + session summaries when
    a session is wrapping up (write side of the flywheel)
  - `open-brain-live-retrieval` — silently surfaces relevant thoughts on
    topic shifts during active work (read side of the flywheel)
  - `open-brain-daily-digest` — on-demand summary of recent brain activity
- **Upstream-compatible capture** using the same direct INSERT pattern as the
  MCP server. If the optional `upsert_thought` RPC is installed (OB1 setup
  step 2.6), it is used for SHA-256 content-fingerprint dedup automatically.
- **Source filtering** on every read tool (`search`, `list`, `stats`,
  `recall`, `digest`) — scope to `agent_zero`, `gmail`, `chatgpt`, `obsidian`,
  or any source tag you use (per [OB1 recipes/source-filtering](https://github.com/NateBJones-Projects/OB1/tree/main/recipes/source-filtering)).
- **Prompt-injection sanitization** on every capture so thoughts retrieved
  months later by another AI cannot be used to attack downstream agents.
- **Secret masking** in the config API and WebUI dashboard — keys are never
  returned in the clear once saved.

## Quick Start

1. **Prerequisite**: A working OB1 Supabase project. If you don't have one,
   follow [OB1 docs/01-getting-started.md](https://github.com/NateBJones-Projects/OB1/blob/main/docs/01-getting-started.md)
   first (~30 min). You need the `thoughts` table and `match_thoughts` RPC
   (setup steps 2.2, 2.3). Step 2.6 (`upsert_thought`) is optional for dedup.
2. **Install the plugin:**
   ```bash
   ./install.sh
   ```
3. **Configure credentials** in the Agent Zero WebUI:
   Settings → External Services → Open Brain → Credentials tab. Paste:
   - Supabase Project URL
   - Supabase Secret Key
   - OpenRouter API Key
4. **Restart Agent Zero** (or click *Init* on the plugin card).
5. **Click *Test Connection*** in the Open Brain dashboard.

## Documentation

- [Quick Start](docs/QUICKSTART.md) — First capture + first search in 5 min
- [Setup](docs/SETUP.md) — Full credential setup, Supabase prerequisites
- [Development](docs/DEVELOPMENT.md) — Architecture, extending the plugin

## Credit

The Open Brain system (schema, RPC functions, MCP server, canonical skills)
is the work of [@NateBJones-Projects](https://github.com/NateBJones-Projects)
and the OB1 community. This plugin is an Agent Zero client for that system —
it does not fork OB1. See [OB1](https://github.com/NateBJones-Projects/OB1)
for upstream docs, recipes, and extensions.

## License

MIT — see [LICENSE](LICENSE).
