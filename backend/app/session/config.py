from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

ALLOWED_MIXES = {(2, 1), (3, 0), (1, 2)}  # (humans, ai)
KEYS = {
    "humans",
    "ai",
    "chat_seconds",
    "vote_seconds",
    "start_delay_min_seconds",
    "start_delay_max_seconds",
    "waiting_grace_seconds",
    "ai_model",
    "ai_call_timeout_seconds",
}


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    humans: int
    ai: int
    chat_seconds: int
    vote_seconds: int
    start_delay_min_seconds: int
    start_delay_max_seconds: int
    waiting_grace_seconds: int
    ai_model: str
    ai_call_timeout_seconds: int

    def snapshot(self) -> dict:
        return asdict(self)


def _int(raw: dict, key: str, minimum: int) -> int:
    value = raw.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ConfigError(f"config: '{key}' must be an integer >= {minimum}")
    return value


def _str(raw: dict, key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"config: '{key}' must be a non-empty string")
    return value.strip()


def load_config(path: str) -> Config:
    try:
        raw = yaml.safe_load(Path(path).read_text())
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"config: cannot read {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError("config: expected a YAML mapping")
    unknown = set(raw) - KEYS
    if unknown:
        raise ConfigError(f"config: unknown keys {sorted(unknown)}")
    config = Config(
        humans=_int(raw, "humans", 1),
        ai=_int(raw, "ai", 0),
        chat_seconds=_int(raw, "chat_seconds", 1),
        vote_seconds=_int(raw, "vote_seconds", 1),
        start_delay_min_seconds=_int(raw, "start_delay_min_seconds", 0),
        start_delay_max_seconds=_int(raw, "start_delay_max_seconds", 0),
        waiting_grace_seconds=_int(raw, "waiting_grace_seconds", 1),
        ai_model=_str(raw, "ai_model"),
        ai_call_timeout_seconds=_int(raw, "ai_call_timeout_seconds", 1),
    )
    if config.start_delay_max_seconds < config.start_delay_min_seconds:
        raise ConfigError("config: start_delay_max_seconds must be >= start_delay_min_seconds")
    if (config.humans, config.ai) not in ALLOWED_MIXES:
        raise ConfigError(
            "config: humans/ai must be one of 2/1, 3/0 or 1/2, "
            f"got {config.humans}/{config.ai}"
        )
    return config
