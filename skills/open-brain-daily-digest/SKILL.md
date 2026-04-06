---
name: open-brain-daily-digest
description: |
  Produce a human-readable daily (or weekly / monthly) digest of recent Open Brain
  activity on demand. Use when the user asks "what's been in my brain lately?",
  "give me a digest", "catch me up on this week", or "what did we capture
  yesterday?". Wraps the open_brain_digest tool with an optional LLM narration
  pass for a more readable output. Based on the OB1 daily-digest recipe
  (https://github.com/NateBJones-Projects/OB1/blob/main/recipes/daily-digest/README.md).
author: Travel Jamboree
version: 1.0.0
---

# Open Brain — Daily Digest

An on-demand summary of recent Open Brain captures. Deterministic: the numbers
and breakdowns come straight from the metadata already attached to each
thought, so the digest does not hallucinate.

## When to fire

- User asks "what's in my brain?", "give me a digest", "catch me up"
- User asks "what did I capture [yesterday / this week / this month]?"
- User wants to start a planning session and needs the landscape first
- A named project or date is referenced and the user wants a recap

Do **not** fire spontaneously. This is a user-requested skill.

## Process

1. Pick the window:
   - "yesterday" / "today" → `days: 1`
   - "this week" → `days: 7`
   - "this month" → `days: 30`
   - Otherwise ask, or default to `days: 7`.
2. Call `open_brain_digest` with the chosen `days`. Include `source` if the
   user asked for a specific source (e.g. "what have I captured from Gmail
   this week?").
3. Read the result. It contains:
   - Total thoughts in the window
   - Breakdown by type
   - Top topics and people
   - Source mix (if not already scoped)
   - Open action items
   - Highlight thoughts
4. Optionally narrate. If the user wants a story instead of a report, pass the
   digest text into your reasoning step and write a 3–5 sentence narrative
   that ties the themes together. Keep the numbers verbatim — do not
   hallucinate counts.
5. End with a short "what's next?" paragraph that lists the open action
   items and invites the user to pick one.

## Output shape

Default output (when the user asks for a report):

```
Open Brain digest — last 7 days

Total thoughts: 42

By type:
  task: 14
  observation: 13
  ...

Top topics: ...
People mentioned: ...

Open action items:
  - ...
  - ...

Highlights:
  [date] ...
```

Narrated output (when the user asks for a summary or story): a short paragraph
plus the action items list.

## Rules

1. **Numbers are ground truth.** Never invent counts or topic names.
2. **Action items come from captured metadata**, not from inference. If the
   digest tool shows no open action items, the narrative should not invent
   them.
3. **Highlight the surprising, not the routine.** If the user captures 10
   social-media observations every day, "captured social media observations"
   is not a highlight.
4. **Respect privacy.** Do not paste person names or sensitive content into
   external tools for narration — use the agent's own reasoning step.

## Failure behavior

- If `open_brain_digest` returns "No thoughts captured", tell the user so
  plainly and suggest they capture something first.
- If the plugin is not configured, point them at the Setup Guide rather than
  running the tool.
