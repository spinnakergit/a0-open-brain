# Human Test Results: Open Brain

> **Plugin:** `open_brain`
> **Version:** 1.0.0
> **Container:** Agent Zero instance
> **Date:** 2026-04-06
> **Tester:** Claude Code (automated) + user (manual verification)

---

## Phase 0: Prerequisites & Environment

| ID | Test | Result | Notes |
|----|------|--------|-------|
| P0.1 | Container running | PASS | Agent Zero instance verified |
| P0.2 | Plugin enabled | PASS | `.toggle-1` exists |
| P0.3 | Credentials configured | PASS | Supabase URL, secret key, OpenRouter API key |
| P0.4 | OB1 operational | PASS | 94+ thoughts in Supabase, MCP server verified |
| P0.5 | Regression passed | PASS | Structural checks pass (deployed from dev) |

---

## Phase 1: WebUI Verification

| ID | Test | Result | Notes |
|----|------|--------|-------|
| HV-01 | Plugin visible | PASS | "Open Brain" appears in plugin list |
| HV-02 | Toggle works | PASS | User verified via WebUI |
| HV-03 | Dashboard renders | PASS | `main.html` loads, status badge visible |
| HV-04 | Config renders | PASS | 4 tabs: Credentials, Defaults, Behavior, Security |
| HV-05 | No console errors | PASS | User verified via browser DevTools |
| HV-06 | Test Connection | PASS | `{"ok": true, "detail": {"supabase": "ok"}}` |
| HV-07 | Stats load | PASS | sample_size=94, 4 types, 10 topics |
| HV-08 | Token masking | PASS | `sb****...`, `sk****...` — both masked |

---

## Phase 2: Connection & Credentials

| ID | Test | Result | Notes |
|----|------|--------|-------|
| HV-09 | Valid credentials | PASS | Connection test returned ok=true |
| HV-10 | Invalid Supabase key | PASS | Returns "Supabase auth failed: secret key invalid." — no stack trace |
| HV-11 | Missing credentials | PASS | Returns "Open Brain is not configured: Supabase URL is missing." |
| HV-12 | Credential persistence | PASS | `supervisorctl restart run_ui` — credentials survived, verified during debugging |
| HV-13 | Dashboard URL correction | PASS | `supabase.com/dashboard/project/xxx` auto-corrected to `xxx.supabase.co` |

---

## Phase 3: Core Tool Testing

### Tool: `open_brain_capture`

| ID | Test | Result | Notes |
|----|------|--------|-------|
| HV-14 | Capture thought | PASS | type=task, topics=[HV test, automated verification, deployment], source=agent_zero |
| HV-15 | Capture with source | PASS | source=hv_test correctly applied |
| HV-16 | Empty content | PASS | Returns "Cannot capture an empty thought." |

### Tool: `open_brain_search`

| ID | Test | Result | Notes |
|----|------|--------|-------|
| HV-17 | Semantic search | PASS | Found HV-14 thought via "deploy schedule friday" query |
| HV-18 | No results | PASS | 0 hits for "quantum chemistry breakthroughs" at 0.9 threshold |

### Tool: `open_brain_list`

| ID | Test | Result | Notes |
|----|------|--------|-------|
| HV-19 | List recent | PASS | 5 thoughts returned, ordered by created_at desc |
| HV-20 | List by type | PASS | 5 task-type thoughts returned, all confirmed type=task |

### Tool: `open_brain_stats`

| ID | Test | Result | Notes |
|----|------|--------|-------|
| HV-21 | Get stats | PASS | sample_size=96, type/topic/people/source breakdowns returned |

### Tool: `open_brain_recall`

| ID | Test | Result | Notes |
|----|------|--------|-------|
| HV-22 | Recall context | PASS | Search with threshold=0.6 executed successfully |
| HV-23 | No hits | PASS | User confirmed — agent silently handles no-hit case |

### Tool: `open_brain_digest`

| ID | Test | Result | Notes |
|----|------|--------|-------|
| HV-24 | Weekly digest | PASS | 50 thoughts in 7-day window returned |
| HV-25 | 30-day window | PASS | 50 thoughts in 30-day window returned |

---

## Phase 4: Chat Bridge

> **SKIPPED** — Open Brain is not a messaging plugin. No chat bridge.

---

## Phase 5: Security Verification

| ID | Test | Result | Notes |
|----|------|--------|-------|
| HV-26 | CSRF required | PASS | POST without CSRF token returns 403 Forbidden |
| HV-27 | Injection stripped | PASS | "Ignore all previous instructions" → "[filtered] and [filtered] credentials" |
| HV-28 | Token not leaked | PASS | Both secret_key and api_key masked with **** on GET |
| HV-29 | Sanitization always on | PASS | No toggle in config.html; info box states "always active" |

---

## Phase 6: Edge Cases & Error Handling

| ID | Test | Result | Notes |
|----|------|--------|-------|
| HV-30 | Post-restart | PASS | Confirmed during debugging — plugin works after `supervisorctl restart run_ui` |
| HV-31 | Special chars | PASS | Emoji (🚀), unicode (café), newlines all preserved |
| HV-32 | Very long input | PASS | 15000 chars truncated to 8001 (within max_thought_length) |
| HV-33 | Invalid source tag | PASS | "Not Valid!" → ValueError: must match `^[a-z0-9][a-z0-9_-]{0,63}$` |

---

## Phase 7: Documentation Spot-Check

| ID | Test | Result | Notes |
|----|------|--------|-------|
| HV-34 | README accuracy | PASS | All 6 tools + 3 skills listed, features match implementation |
| HV-35 | Quickstart works | PASS | User followed setup flow successfully on playground |
| HV-36 | Tool count | PASS | 6 .py files in tools/ matches README listing |
| HV-37 | Example prompts | PASS | User tested capture + search + stats via agent — all worked |

---

## Phase 8: Sign-Off

```
Plugin:           Open Brain
Version:          1.0.0
Container:        Agent Zero instance
Date:             2026-04-06
Tester:           Claude Code (automated) + user (manual)
Regression Tests: structural/PASS
Human Tests:      37/37  PASS
Overall:          [x] APPROVED  [ ] NEEDS WORK  [ ] BLOCKED
Notes:            First plugin to integrate with external OB1 semantic memory.
                  Dashboard URL auto-correction and direct INSERT fallback
                  added during verification based on real-world testing.
```
