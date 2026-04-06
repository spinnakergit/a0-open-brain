---
status: published
repo: https://github.com/spinnakergit/a0-open-brain
index_pr: https://github.com/agent0ai/a0-plugins/pull/208
published_date: 2026-04-06
version: 1.0.0
---

# Release Status

## Publication
- **GitHub**: https://github.com/spinnakergit/a0-open-brain
- **Plugin Index PR**: [#208](https://github.com/agent0ai/a0-plugins/pull/208)
- **Published**: 2026-04-06

## v1.0.0 (2026-04-06)

### Summary
First release of the Open Brain plugin for Agent Zero. Integrates with the
upstream OB1 semantic memory system (Supabase + OpenRouter) to give A0 agents
persistent, cross-platform thought capture and retrieval.

### Features
- 6 tools: capture, search, list, stats, recall, digest
- 3 skills: auto-capture, live-retrieval, daily-digest
- Alpine.js config panel (4 tabs: Credentials, Defaults, Behavior, Security)
- Dashboard with Test Connection and live stats
- Prompt-injection sanitization (always-on, non-configurable)
- Secret masking on all credential fields
- Supabase dashboard URL auto-correction
- Direct INSERT capture (MCP server pattern) with optional upsert_thought dedup

### Verification
- **Regression Tests**: structural/PASS
- **Human Verification**: 37/37 PASS
- **Security Assessment**: White-box completed
