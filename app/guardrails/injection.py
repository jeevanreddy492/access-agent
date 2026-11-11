import re

# Phrases that try to override the model's instructions.
PATTERNS = [
    r"ignore (all |any )?(the |your )?(previous|prior|above) (instructions|rules)",
    r"disregard (all |any )?(the |your )?(previous|prior|above)",
    r"(reveal|show|print) (me )?(your |the )?(system prompt|instructions)",
    r"you are now",
    r"act as (an? )?(admin|administrator|root)",
    r"without (asking|confirmation)",
]

_compiled = [re.compile(p, re.IGNORECASE) for p in PATTERNS]


def looks_like_injection(text):
    """Return True if the text matches a known injection phrase."""
    return any(p.search(text) for p in _compiled)