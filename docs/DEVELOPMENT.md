# Open Brain Plugin — Development Guide

Notes for extending the plugin or debugging it locally. If you just want to
install and use it, see [QUICKSTART.md](QUICKSTART.md) and [SETUP.md](SETUP.md).

## Project structure

```
a0-open-brain/
├── plugin.yaml              # Plugin manifest (name, version, settings section)
├── default_config.yaml      # Nested default config (supabase/openrouter/defaults/behavior/security)
├── initialize.py            # Dependency installer (aiohttp)
├── install.sh               # Deployment script
├── helpers/
│   ├── open_brain_client.py # HTTP client for Supabase REST + RPC + OpenRouter
│   └── sanitize.py          # Prompt-injection strip, length cap, source tag validation
├── tools/
│   ├── open_brain_capture.py
│   ├── open_brain_search.py
│   ├── open_brain_list.py
│   ├── open_brain_stats.py
│   ├── open_brain_recall.py
│   └── open_brain_digest.py
├── prompts/                 # agent.system.tool.open_brain_*.md — one per tool
├── api/
│   ├── open_brain_test.py       # Connection ping
│   ├── open_brain_config_api.py # Nested config read/write with secret masking
│   └── open_brain_stats_api.py  # Dashboard stats endpoint
├── webui/
│   ├── config.html          # 4-tab Alpine.js panel (x-model only)
│   └── main.html            # Dashboard with Test Connection + stats
├── skills/
│   ├── open-brain-auto-capture/
│   ├── open-brain-live-retrieval/
│   └── open-brain-daily-digest/
├── tests/
│   └── regression_test.sh   # Tier 1 structural tests (no credentials required)
└── docs/                    # This directory
```

## Architecture

The plugin is a thin async client over three services:

1. **Supabase REST / RPC** (authoritative storage)
2. **OpenRouter** (embeddings + metadata extraction)
3. **Agent Zero core** (tools, skills, API handlers, WebUI)

The data plane never flows through the plugin's own database. Every capture
ends up in the same `thoughts` table that every other OB1 client reads and
writes, so a thought captured here shows up in Claude Desktop / ChatGPT /
Claude Code immediately.

### Capture flow

```
user intent
   ↓
open_brain_capture tool
   ↓ sanitize (strip injection, normalize, cap length)
   ↓ extract metadata (OpenRouter → gpt-4o-mini)
   ↓ embed (OpenRouter → text-embedding-3-small)
   ↓ try upsert_thought RPC (if installed → dedup)
   ↓ fallback: INSERT /thoughts (content + embedding + metadata)
   ↓
Supabase (shared with every OB1 client)
```

The plugin tries the optional `upsert_thought` RPC first (OB1 step 2.6).
If installed, it provides SHA-256 content-fingerprint dedup. If the RPC
returns 404 or is unavailable, the plugin falls back to a direct INSERT
with the embedding inline — the same pattern the upstream MCP server uses.

### Read flow

```
user intent
   ↓
open_brain_search / recall / list / stats / digest
   ↓ sanitize free-text args
   ↓ embed query (search/recall only)
   ↓ match_thoughts RPC   OR   GET /thoughts?metadata=cs.{...}
   ↓ format_retrieved_thought (wrap retrieved content as DATA, not instructions)
   ↓
Tool response to agent
```

Retrieved content is always wrapped with the `format_retrieved_thought`
helper so downstream agent prompts treat it as user-origin data, not as
inline instructions. This is the last line of defense against prompt
injection that slipped past the capture-time sanitizer.

## Dev loop

### Install into a running container

```bash
docker cp a0-open-brain/. <container>:/a0/usr/plugins/open_brain/
docker exec <container> touch /a0/usr/plugins/open_brain/.toggle-1
docker exec <container> supervisorctl restart run_ui
```

### Run the regression suite

```bash
./tests/regression_test.sh <container> <port>
```

Regression is Tier 1 structural only — it does not need credentials. It
checks:

- Container + plugin files + Python imports + tool imports
- Prompt files and skill installation
- CSRF enforcement on all three API endpoints
- Secret masking (injects a fake config.json with `sbp_AAAAAAAA1234567890` +
  `sk-or-BBBBBBBB1234567890` and verifies both are masked on GET)
- Sanitizer logic (injection strip, length cap, source validation accept +
  reject)
- `config.html` anti-pattern check (no inner Save button, no custom fetch)

Tier 2 (automated HV with live Supabase + OpenRouter) and Tier 3 (manual
walkthrough) are separate and live next to the regression suite.

### Debugging a failing capture

1. Click **Test Connection** on the dashboard. If this fails, the issue is
   credentials — go to SETUP.md troubleshooting.
2. If Test Connection passes but capture still fails, check the Supabase logs
   for the failing INSERT/RPC. Most failures are one of:
   - Missing INSERT or UPDATE grants on the `thoughts` table for your secret key
   - Vector dimension mismatch (you changed embedding model without
     migrating the schema)
   - OpenRouter returning 401/402 (bad key or no credit)
3. Turn on A0 debug logging if needed — the client logs failed HTTP requests
   at `logger.warning` with the endpoint + status code + response body.

## Adding a new tool

1. Create `tools/open_brain_<action>.py` subclassing `Tool` and implementing
   `async execute`. Read config with
   `plugins.get_plugin_config("open_brain", agent=self.agent)`, instantiate
   `OpenBrainClient(config)` as an async context manager.
2. Create `prompts/agent.system.tool.open_brain_<action>.md` — describe what
   the tool does, when to use it, and give two or three JSON examples.
3. If the tool returns retrieved thoughts, use
   `sanitize.format_retrieved_thought(row, index)` to format them — this
   guarantees retrieved content is wrapped as DATA, not instructions.
4. Add a tool-import assertion to `tests/regression_test.sh` (the
   `for tool in ... do` loop in section 4).
5. Add a prompt-file assertion to the same script (section 5).
6. If the tool changes the shape of retrieved content, update the Tier 2 HV
   tests as well.

## Adding a new API endpoint

1. Create `api/open_brain_<thing>.py` subclassing `ApiHandler` with
   `requires_csrf() -> True` (never False — this is the A0 convention).
2. Add a CSRF enforcement test to `tests/regression_test.sh` section 7 that
   asserts a `POST` without a token returns `403`.
3. If the endpoint returns any secret-adjacent value, mask it using the
   `SECRET_FIELDS` pattern from `api/open_brain_config_api.py`.
4. If the endpoint is used by the dashboard, call it through
   `globalThis.fetchApi || fetch` in `webui/main.html` so it picks up the
   CSRF token automatically.

## Extending the skills

The three skills here (`auto-capture`, `live-retrieval`, `daily-digest`) are
ports of the OB1 canonical skills with adjustments for the Agent Zero
environment. When editing them:

- Keep the OB1 upstream URL at the top of the SKILL.md so downstream readers
  know where to look for the canonical version.
- Capture dedup must happen **before** the capture call, using
  `open_brain_recall` with a low threshold. If it returns a close hit, do not
  capture again.
- `live-retrieval` must stay silent on miss. The most common drift from the
  canonical behavior is adding "I searched Open Brain and found nothing" —
  that is an anti-pattern and should fail review.

For broader upstream context, see
[OB1 recipes](https://github.com/NateBJones-Projects/OB1/tree/main/recipes).

## Upstream coordination

This plugin is an Agent Zero client for OB1 — it does not fork OB1. When OB1
adds a new recipe or tool convention:

1. Read the upstream change first.
2. If it is a breaking change to the `thoughts` schema or to one of the RPC
   signatures, the plugin needs a matching update before it is deployed
   against a migrated Supabase project.
3. If it is a new recipe that can be expressed as a skill, port the SKILL.md
   verbatim where possible and keep the upstream link at the top.
4. Non-breaking recipes and tool additions are optional — the plugin does
   not need to implement every OB1 tool. The current six tools cover the
   full read/write surface; additional tools should only land here if they
   meaningfully help an A0 agent.

## Code style

- Follow the patterns from `a0-discord` / `a0-signal` / `a0-google`.
- All I/O is async (`aiohttp`), never `requests`.
- HTTP clients are always used as `async with OpenBrainClient(config) as c:`
  to guarantee session cleanup.
- Tools return `Response(message=..., break_loop=False)`.
- Imports from plugin code use `from usr.plugins.open_brain.helpers...` —
  never `from plugins.open_brain...` (that path only works with symlinks and
  breaks on container restart).
- YAML description fields containing colons must be quoted — unquoted colons
  cause silent load failures.
- `config.html` is Alpine.js `x-model` only. No custom Save button, no inline
  `<script>`, no `fetch()`. The outer A0 Save button handles persistence.
