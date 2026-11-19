import re

MAX_CHARS = 110
MAX_WORDS = 18

# The only content filter: a plain admission of being an AI. Anything else about
# how the AI presents itself is left to the prompt, not to a word list.
ADMISSION = re.compile(
    r"\b(?:i'?m|im|i am|as) (?:just )?(?:an? )?"
    r"(?:ai|a\.i\.?|artificial intelligence|language model|llm|chatbot|bot|robot)\b",
    re.IGNORECASE,
)
LABEL = re.compile(r"\bPlayer ([ABC])\b")
_PREFIX = re.compile(r"^\s*(?:\*\*)?Player [ABC](?:\s*\(you\))?(?:\*\*)?\s*[:\-–]\s*", re.IGNORECASE)


def _normal(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def clean_chat(raw: str, previous: list[str]) -> tuple[str | None, str]:
    """Check a model's chat message before it can be posted. Returns the cleaned
    text, or None with the reason it was rejected. Only a plain admission of being
    an AI is filtered by content; the rest are format checks (single short line,
    not empty, not a repeat)."""
    text = raw.strip().splitlines()[0].strip() if raw.strip() else ""
    text = _PREFIX.sub("", text).strip().strip("\"'`“”")
    if not text:
        return None, "empty"
    if ADMISSION.search(text):
        return None, "admission"
    if len(text) > MAX_CHARS or len(text.split()) > MAX_WORDS:
        return None, "too_long"
    if _normal(text) in {_normal(p) for p in previous}:
        return None, "duplicate"
    return text, "ok"


def parse_vote(raw: str, allowed: list[str]) -> str | None:
    """Exactly one distinct player must be named, and it must be one the voter
    is allowed to pick."""
    named = {f"Player {m}" for m in LABEL.findall(raw)}
    if len(named) != 1:
        return None
    choice = named.pop()
    return choice if choice in allowed else None
