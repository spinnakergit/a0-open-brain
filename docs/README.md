# Open Brain Plugin Documentation

## Overview

Unified semantic memory for Agent Zero. This plugin connects A0 to the user's
existing [Open Brain (OB1)](https://github.com/NateBJones-Projects/OB1)
Supabase project so every agent can read from and write to the same long-term
memory shared with Claude Desktop, ChatGPT, Claude Code, and every other OB1
client.

## Contents

- [QUICKSTART.md](QUICKSTART.md) — First capture + first search in 5 minutes
- [SETUP.md](SETUP.md) — Full credential setup + Supabase prerequisites
- [DEVELOPMENT.md](DEVELOPMENT.md) — Architecture, extending the plugin

## Architecture

```
┌────────────────────────┐        ┌──────────────────────────┐
│  Agent Zero (any A0)   │        │  Other OB1 clients:      │
│  Open Brain plugin     │        │  Claude Desktop, ChatGPT │
│  - 6 tools             │        │  Claude Code, etc.       │
│  - 3 skills            │        └────────────┬─────────────┘
│  - WebUI dashboard     │                     │
└──────────┬─────────────┘                     │
           │ REST + RPC                        │ MCP remote
           ▼                                   ▼
    ┌────────────────────────────────────────────────┐
    │  Supabase project                              │
    │  - thoughts table (content + embedding + meta) │
    │  - match_thoughts() RPC  (semantic search)     │
    │  - upsert_thought() RPC  (optional, dedup)      │
    └────────────────────────────────────────────────┘
                    ▲
                    │ embeddings + metadata extraction
                    │
            ┌───────────────┐
            │  OpenRouter   │
            │  - embeddings │
            │  - chat       │
            └───────────────┘
```

The plugin does **not** run its own MCP server, and it does **not** store a
separate copy of any thoughts. It is a direct client of the user's Supabase
project, using the same RPC functions the upstream OB1 MCP server uses.

## Tools

| Tool | Description |
|------|-------------|
| `open_brain_capture` | Save a thought. Auto-embeds + extracts metadata. Content-fingerprint dedup. |
| `open_brain_search` | Semantic search via the `match_thoughts` RPC. Source-filterable. |
| `open_brain_list` | Browse recent thoughts by exact metadata filters (type, topic, person, source, time window). |
| `open_brain_stats` | Summary stats: totals, types, top topics, top people, source mix. |
| `open_brain_recall` | High-signal recall tuned for agent workflows — stricter threshold, dedup, multi-source fan-out. |
| `open_brain_digest` | Human-readable digest of recent activity for "what's in my brain?" questions. |

## Skills

| Skill | Role | OB1 upstream |
|-------|------|--------------|
| `open-brain-auto-capture` | Write side of the flywheel — captures ACT NOW items + session summary on session close | [auto-capture](https://github.com/NateBJones-Projects/OB1/blob/main/skills/auto-capture/SKILL.md) |
| `open-brain-live-retrieval` | Read side — silently surfaces relevant thoughts on topic shifts | [live-retrieval](https://github.com/NateBJones-Projects/OB1/blob/main/recipes/live-retrieval/live-retrieval.skill.md) |
| `open-brain-daily-digest` | On-demand digest of recent activity | [daily-digest](https://github.com/NateBJones-Projects/OB1/tree/main/recipes/daily-digest) |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/plugins/open_brain/open_brain_test` | POST | Supabase ping (verify URL + secret key + table + grants) |
| `/api/plugins/open_brain/open_brain_config_api` | GET/POST | Read/write plugin configuration (secrets masked on GET) |
| `/api/plugins/open_brain/open_brain_stats_api` | POST | Stats for the WebUI dashboard |

All three endpoints require the standard A0 CSRF token.

## Security

- Every captured thought is sanitized (prompt-injection strip, unicode
  normalization, length cap) before it is written.
- Free-text tool arguments are sanitized before they are embedded or used as
  filters.
- Supabase secret key and OpenRouter API key are never returned in cleartext
  from the config API — they are masked as `AA****ZZ`.
- `config.json` is written 0600 with atomic rename.
- Config API requires CSRF; tools run as the user's agent and never expose
  their credentials to retrieved content.
- RLS is not bypassed by the plugin — the user's Supabase project handles
  authorization via `service_role` grants. If you want per-user isolation
  inside a shared Supabase project, see [OB1 primitives/rls](https://github.com/NateBJones-Projects/OB1/tree/main/primitives/rls).
