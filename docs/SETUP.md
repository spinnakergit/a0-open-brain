# Open Brain Plugin — Setup Guide

This guide walks through the full credential setup for the Open Brain plugin,
including the Supabase prerequisites on the OB1 side and the troubleshooting
steps for the most common issues.

## Overview

The plugin needs three credentials:

| Credential | Where it comes from | Used for |
|------------|--------------------|---------|
| **Supabase Project URL** | Your OB1 Supabase project settings | REST + RPC endpoints |
| **Supabase Secret Key** | Your OB1 Supabase project API keys | Authorization against `thoughts` / `match_thoughts` |
| **OpenRouter API Key** | [openrouter.ai](https://openrouter.ai) account settings | Embeddings + metadata extraction |

Nothing else is required. The plugin does not run its own MCP server and does
not maintain a separate copy of the data — it talks directly to the same
Supabase project that every other OB1 client (Claude Desktop, ChatGPT, Claude
Code, etc.) uses.

## Step 1 — Make sure OB1 is set up

If you have never configured OB1 before, do that first. The upstream docs
walk you through every step:

- [docs/01-getting-started.md](https://github.com/NateBJones-Projects/OB1/blob/main/docs/01-getting-started.md)
- [docs/02-setup-details.md](https://github.com/NateBJones-Projects/OB1/blob/main/docs/02-setup-details.md)

The specific database objects this plugin needs are:

| Object | OB1 setup step | Purpose |
|--------|----------------|---------|
| `thoughts` table with `embedding vector(1536)` + `metadata jsonb` + `content_fingerprint text` | 2.2 | Storage |
| `match_thoughts(query_embedding, match_threshold, match_count, filter)` RPC | 2.3 | Semantic search |
| `upsert_thought(p_content, p_payload)` RPC | 2.6 | Optional — fingerprint dedup on capture |
| `pgvector` extension | Prereq | Vector similarity |

> **Step 2.6 is optional.** If `upsert_thought` is installed, the plugin
> uses it automatically for content-fingerprint dedup (capturing the same
> thought twice merges metadata instead of duplicating rows). Without it,
> the plugin falls back to direct INSERT — the same pattern the upstream
> MCP server uses.

## Step 2 — Collect the three credentials

### Supabase Project URL + Secret Key

1. Open your [Supabase dashboard](https://supabase.com/dashboard) and select
   your OB1 project.
2. Go to **Project Settings → API**.
3. Copy **Project URL** — this is your Supabase Project URL.
4. Under **Project API keys**, copy the `service_role` key (starts with
   `eyJ...`) — this is your Supabase Secret Key.

> The `service_role` key bypasses RLS. If you want per-user isolation inside
> a shared project, use a scoped secret key instead and follow
> [OB1 primitives/rls](https://github.com/NateBJones-Projects/OB1/tree/main/primitives/rls)
> to set up row-level security. The plugin works with either — it only needs
> grants on `thoughts` and `match_thoughts` (plus `upsert_thought` if
> step 2.6 is installed).

### OpenRouter API Key

1. Sign in at [openrouter.ai](https://openrouter.ai).
2. Go to **Settings → Keys**.
3. Create a new key (or reuse an existing one). It starts with `sk-or-`.
4. Make sure your account has credit balance — embeddings are cheap
   (thousandths of a cent per capture) but not free.

## Step 3 — Enter the credentials in Agent Zero

1. Open the Agent Zero WebUI.
2. Go to **Settings → External Services → Open Brain**.
3. Open the **Credentials** tab and paste all three values.
4. Close the panel. Agent Zero writes the values atomically to a
   `config.json` with 0600 permissions.

Secrets are masked as `AA****ZZ` on subsequent reads. Leaving the masked
value in place when re-saving preserves the original — only changing the
field to a new cleartext value will overwrite the stored secret.

## Step 4 — Configure defaults (optional)

Open the **Defaults** tab if you want to tune:

| Setting | Default | Notes |
|---------|---------|-------|
| Default source tag | `agent_zero` | Source tag written onto every thought captured by this plugin |
| Result limit | `10` | How many hits to return from `open_brain_search` by default |
| Match threshold | `0.5` | Minimum similarity for `match_thoughts` |
| Recall score threshold | `0.6` | Stricter threshold for the agent-tuned `open_brain_recall` |
| Embedding model | `openai/text-embedding-3-small` | Must match OB1's 1536-dim vector column |
| Extraction model | `openai/gpt-4o-mini` | Used for metadata extraction at capture time |

> **Do not change the embedding model unless you change OB1's vector
> dimension to match.** OB1 ships with `vector(1536)` which is the right size
> for `text-embedding-3-small`. Larger models require a schema migration.

## Step 5 — Configure behavior (optional)

Open the **Behavior** tab if you want to adjust the flywheel skills:

| Setting | Default | Notes |
|---------|---------|-------|
| Auto-capture | `on` | When a session wraps up, capture ACT NOW items + summary |
| Live retrieval | `on` | On topic shifts, silently fetch relevant thoughts |
| Max retrievals per session | `3` | Cap on live-retrieval firings per session |

The skills live under `/a0/usr/skills/open-brain-*` and are installed
alongside the plugin.

## Step 6 — Test the connection

Open the **Dashboard** (main view of the Open Brain plugin card) and click
**Test Connection**. You should see:

```
OK — N thought(s) reachable
```

where N is the count visible to your service role in the `thoughts` table.

## Troubleshooting

### "Supabase URL is not configured" / "Supabase secret key is not configured"

Go back to the Credentials tab. At least one field is empty. Close the
settings panel after pasting — the plugin persists the values on close, not
on each keystroke.

### "Supabase returned HTTP 401 Unauthorized"

- Your secret key is wrong or revoked — copy it again from the Supabase
  dashboard.
- Or your secret key is correct but does not have grants on the `thoughts`
  table or RPC functions. See OB1 setup step 2.2 for the required grants.

### "Supabase returned HTTP 404 Not Found" when searching

You are missing the `match_thoughts` RPC. Run OB1 setup step 2.3 on your
Supabase project.

### Captures fail with HTTP errors

If the plugin cannot INSERT into the `thoughts` table, check that your
secret key has INSERT and UPDATE grants on `public.thoughts`. If you have
the optional `upsert_thought` RPC installed (step 2.6), also confirm
EXECUTE grants on it.

### "relation \"public.thoughts\" does not exist"

You are missing the `thoughts` table. Run OB1 setup step 2.2 on your Supabase
project. Make sure you created it in the `public` schema.

### "OpenRouter returned HTTP 401"

Your OpenRouter API key is wrong or expired. Create a new one at
openrouter.ai and paste it into the Credentials tab.

### "OpenRouter returned HTTP 402 / 429"

You are out of OpenRouter credit or are being rate limited. Top up at
openrouter.ai and retry. Embeddings are cheap — a few cents per thousand
captures — so a small top-up lasts a long time.

### Thoughts capture but searches return nothing

- Check that the embedding model in the Defaults tab matches OB1's vector
  dimension (1536 by default).
- Check that the match threshold is not set too high — start at `0.5` and
  tighten from there.
- Check that the `match_thoughts` RPC in your Supabase project uses the same
  `filter jsonb` signature the plugin expects. See
  [OB1 docs/02-setup-details.md](https://github.com/NateBJones-Projects/OB1/blob/main/docs/02-setup-details.md)
  for the canonical definition.

### Test Connection returns OK but tools fail with `HTTP 403`

Your secret key has SELECT on `thoughts` but lacks EXECUTE on the RPC
functions. Grant it via:

```sql
GRANT EXECUTE ON FUNCTION public.match_thoughts(vector, float, int, jsonb) TO service_role;
-- Only needed if you installed the optional upsert_thought RPC (step 2.6):
-- GRANT EXECUTE ON FUNCTION public.upsert_thought(text, jsonb) TO service_role;
```

(Adjust the role name if you are using a scoped secret key instead of
`service_role`.)

## Security notes

- `config.json` is written to `/a0/usr/plugins/open_brain/config.json` with
  mode `0600` (owner-read-write only) via atomic rename. No world-readable
  secrets on disk.
- The config API masks `supabase.secret_key` and `openrouter.api_key` on
  every GET. The cleartext values are only ever read from disk at tool
  invocation time.
- All three plugin API endpoints (`open_brain_test`, `open_brain_config_api`,
  `open_brain_stats_api`) require the standard Agent Zero CSRF token.
- Every captured thought is sanitized before write: prompt-injection patterns
  are stripped, unicode is normalized, length is capped. A malicious thought
  cannot inject instructions into future agents that retrieve it.
- Free-text arguments to read tools (queries, filters) are sanitized before
  being embedded or sent to Supabase.
- RLS is not bypassed by the plugin itself — your Supabase project is still
  the source of truth for authorization. For per-user isolation inside a
  shared project, see
  [OB1 primitives/rls](https://github.com/NateBJones-Projects/OB1/tree/main/primitives/rls).
