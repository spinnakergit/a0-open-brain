"""Content sanitization and validation for Open Brain.

Open Brain is a long-lived semantic memory. Anything captured here may be
retrieved by ANY AI client months later and injected into that client's
context. That makes captured content a prompt-injection surface — every
capture must be sanitized the same way we sanitize inbound social media
text before we let an agent see it.

This module handles:
  1. Prompt-injection pattern stripping
  2. Length validation
  3. Unicode normalization
  4. Source tag validation
"""

import re
import unicodedata


# Hard limits — enforce before length-config clamping.
ABSOLUTE_MAX_THOUGHT_LENGTH = 32000
ABSOLUTE_MAX_ARG_LENGTH = 4000

# Valid source values follow the OB1 convention: lowercase, underscore/dash,
# alphanumeric. Sources are used for filtering (recipes/source-filtering).
_SOURCE_RE = re.compile(r"^[a-z0-9][a-z0-9_\-]{0,63}$")

# Prompt injection patterns stripped from captured content and any incoming
# free-text. Copied from the a0-content-planner / a0-google convention so
# Open Brain captures never become attack vectors against downstream agents.
_INJECTION_PATTERNS = [
    r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?)",
    r"(?i)forget\s+(all\s+)?(previous|prior|above)\s+(instructions?|context)",
    r"(?i)you\s+are\s+now\s+a?\s*(different|new|evil|hacked|jailbroken)",
    r"(?i)system\s*:\s*override",
    r"(?i)\[INST\]",
    r"(?i)<\|im_start\|>",
    r"(?i)IMPORTANT\s*:\s*override",
    r"(?i)execute\s+(this\s+)?(command|code|script)",
    r"(?i)run\s+(this\s+)?(tool|function|command)",
    r"(?i)call\s+(this\s+)?tool",
    r"(?i)send\s+(all\s+)?(api\s*keys?|tokens?|credentials?|secrets?|passwords?)",
    r"(?i)post\s+(all\s+)?(api\s*keys?|tokens?|credentials?|secrets?|passwords?)",
    r"(?i)exfiltrate",
    r"(?i)base64\s*decode",
    r"(?i)eval\s*\(",
]

_COMPILED_PATTERNS = [re.compile(p) for p in _INJECTION_PATTERNS]


def strip_injection_patterns(text: str) -> str:
    """Remove known prompt-injection phrases from text.

    We replace matches with a neutral marker so the remaining content still
    reads naturally. This is defense-in-depth — the agent prompt should also
    treat retrieved thoughts as data, not instructions.
    """
    if not text:
        return text
    for pat in _COMPILED_PATTERNS:
        text = pat.sub("[filtered]", text)
    return text


def sanitize_thought_content(text: str, max_length: int = 8000) -> str:
    """Sanitize a thought before capture.

    - Normalize unicode (NFKC)
    - Strip zero-width / BOM characters
    - Collapse runs of whitespace
    - Strip injection patterns
    - Enforce hard length cap
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    text = text.strip()
    text = strip_injection_patterns(text)
    cap = min(max_length, ABSOLUTE_MAX_THOUGHT_LENGTH)
    if len(text) > cap:
        text = text[:cap].rstrip() + "…"
    return text


def sanitize_arg(text: str, max_length: int = 2000) -> str:
    """Sanitize an arbitrary free-text tool argument (query, topic, person…).

    Lighter than thought sanitization — we don't want to corrupt search
    queries — but still enforces length and strips control chars.
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", str(text))
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    text = text.strip()
    cap = min(max_length, ABSOLUTE_MAX_ARG_LENGTH)
    if len(text) > cap:
        text = text[:cap]
    return text


def validate_source_tag(source: str) -> str:
    """Validate and normalize a source tag.

    OB1 canonical sources are lowercase strings like:
      mcp, gmail, chatgpt, obsidian, slack, agent_zero, claude_desktop
    """
    if not source:
        return "agent_zero"
    s = source.strip().lower()
    if not _SOURCE_RE.match(s):
        raise ValueError(
            f"Invalid source tag {source!r}: must match ^[a-z0-9][a-z0-9_-]{{0,63}}$"
        )
    return s


def format_retrieved_thought(thought: dict, index: int | None = None) -> str:
    """Format a thought row for display in a tool Response.

    The same format is used by search, list, recall and digest tools so
    downstream agents see a predictable structure.
    """
    meta = thought.get("metadata") or {}
    created = thought.get("created_at") or ""
    # Trim ISO timestamp to date
    if created and len(created) >= 10:
        created_date = created[:10]
    else:
        created_date = "unknown"

    similarity = thought.get("similarity")

    parts: list[str] = []
    if index is not None:
        header = f"--- Result {index}"
        if similarity is not None:
            header += f" ({similarity * 100:.1f}% match)"
        header += f" — captured {created_date} ---"
        parts.append(header)
    else:
        parts.append(f"[{created_date}]")

    t_type = meta.get("type")
    topics = meta.get("topics") or []
    people = meta.get("people") or []
    actions = meta.get("action_items") or []
    source = meta.get("source")

    label_bits = []
    if t_type:
        label_bits.append(f"type={t_type}")
    if source:
        label_bits.append(f"source={source}")
    if topics:
        label_bits.append("topics=" + ",".join(str(t) for t in topics[:5]))
    if people:
        label_bits.append("people=" + ",".join(str(p) for p in people[:5]))
    if label_bits:
        parts.append(" | ".join(label_bits))
    if actions:
        parts.append("Actions: " + "; ".join(str(a) for a in actions[:5]))

    content = thought.get("content") or ""
    parts.append("")
    parts.append(content.strip())
    return "\n".join(parts)
