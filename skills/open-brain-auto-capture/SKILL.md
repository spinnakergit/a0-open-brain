---
name: open-brain-auto-capture
description: |
  Automatically capture ACT NOW items and a session summary to the user's Open Brain
  when a work session is ending. Fires on behavioral cues like "wrap up", "park this",
  "goodnight", or when a brainstorm / Panning for Gold run produces decisions worth
  preserving. This is the write side of the Open Brain flywheel — the read side is
  the open-brain-live-retrieval skill. Based on the OB1 canonical auto-capture skill
  (https://github.com/NateBJones-Projects/OB1/blob/main/skills/auto-capture/SKILL.md).
author: Travel Jamboree
version: 1.0.0
---

# Open Brain — Auto-Capture

## Problem

High-value decisions and next actions are easy to lose at the end of a session.
If capturing them requires a separate decision, they usually never make it into
Open Brain — and six months later the user has no memory of why a choice was
made.

## Trigger conditions

Fire this skill when any of the following are true:

- The user is clearly ending a session: "wrap up", "park this", "goodnight",
  "let's stop here", "come back to this tomorrow"
- A brainstorm or work session produced ACT NOW items or named decisions worth
  preserving
- A Panning for Gold / research run finished and produced evaluated outputs
- The conversation is about to end and there is clear value in preserving the
  results across future sessions

This is a behavioral protocol, **not** a background hook, timer, or daemon.

## Process

1. Detect that the session is ending (see triggers above).
2. Identify the highest-value outputs from the session:
   - each ACT NOW item or named decision
   - one concise session summary
3. Before capturing, call `open_brain_recall` with the item's strongest key
   phrase and `min_score=0.75`. If a near-duplicate already exists, skip the
   capture and note that it was already known.
4. Capture each ACT NOW item as its own self-contained thought via
   `open_brain_capture`. Each capture should include:
   - The idea in its strongest, standalone form
   - Why it matters (the reason, the constraint, the trigger)
   - 2–3 concrete next actions
   - Provenance when available — the project, date, conversation topic, or
     file the decision came from
5. Capture one session summary via `open_brain_capture` that records:
   - What the session was about
   - How many important items emerged
   - The main themes or threads
   - Where the fuller context lives (file path, project name, chat title)
6. Do not capture low-value noise. Skip:
   - Raw transcript text
   - Parked or killed items
   - Obvious duplicates
   - Anything that was only relevant to the current turn

## Output

When this skill runs correctly, the session ends with:

- One `open_brain_capture` call per ACT NOW item
- One `open_brain_capture` call for the session summary
- Captures specific enough to be useful months later without reopening the
  original session

## Rules

- **Prefer specificity over vague summaries.** "ACT NOW: switch content_assembler
  encoder to two-pass x264 for thumbnails" is useful; "discussed video encoding"
  is not.
- **Include the why.** A decision without a reason is unrecoverable later.
- **Default source tag is `agent_zero`.** Override only when the thought truly
  originates elsewhere (e.g., during a Gmail import workflow).
- **If capture fails, do not invent success.** Tell the user the local wrap-up
  succeeded but the Open Brain capture did not, and suggest they re-run the
  skill after fixing the configuration.

## Notes

This skill is intentionally reusable. The same protocol applies regardless of
the A0 agent that invokes it — social content workflows, QA runs, research
sessions, etc. Source-tag differences alone do not justify forking the skill.
