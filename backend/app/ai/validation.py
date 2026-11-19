import re

MAX_CHARS = 110
MAX_WORDS = 18

# Anything that could disclose player types, the AI count, or what the author is.
DISCLOSURE = re.compile(
    r"\b(ai|a\.i\.?|artificial|bots?|chatbots?|robots?|machines?|algorithms?|llms?|"
    r"language models?|models?|assistants?|programs?|programmed|scripts?|scripted|"
    r"simulat\w*|synthetic|neural|mistral|openai|gpt|chatgpt|claude|gemini|"
    r"humans?|real person|real people|not a person|non-?human|"
    r"real|legit|genuine|i (?:might|may|could) be|(?:yes|yeah|yep|guilty),? (?:i am (?:one|an)|that'?s me)|"
    r"you got me|caught me)\b",
    re.IGNORECASE,
)
LABEL = re.compile(r"\bPlayer ([ABC])\b")
_PREFIX = re.compile(r"^\s*(?:\*\*)?Player [ABC](?:\s*\(you\))?(?:\*\*)?\s*[:\-–]\s*", re.IGNORECASE)


def _normal(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def clean_chat(raw: str, previous: list[str]) -> tuple[str | None, str]:
    """Check a model's chat message before it can be posted. Returns the cleaned
    text, or None with the reason it was rejected."""
    text = raw.strip().splitlines()[0].strip() if raw.strip() else ""
    text = _PREFIX.sub("", text).strip().strip("\"'`“”")
    if not text:
        return None, "empty"
    if DISCLOSURE.search(text):
        return None, "disclosure"
    if len(text) > MAX_CHARS or len(text.split()) > MAX_WORDS:
        return None, "too_long"
    if _normal(text) in {_normal(p) for p in previous}:
        return None, "duplicate"
    return text, "ok"


def parse_vote(raw: str) -> str | None:
    """Exactly one distinct candidate must be named in the model's answer."""
    named = {f"Player {m}" for m in LABEL.findall(raw)}
    return named.pop() if len(named) == 1 else None
