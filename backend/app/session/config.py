from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

ALLOWED_MIXES = {(2, 1), (3, 0), (1, 2)}  # (humans, ai)
KEYS = {"humans", "ai", "chat_seconds", "vote_seconds"}


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    humans: int
    ai: int
    chat_seconds: int
    vote_seconds: int

    def snapshot(self) -> dict:
        return asdict(self)


def _int(raw: dict, key: str, minimum: int) -> int:
    value = raw.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ConfigError(f"config: '{key}' must be an integer >= {minimum}")
    return value


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
    )
    if (config.humans, config.ai) not in ALLOWED_MIXES:
        raise ConfigError(
            "config: humans/ai must be one of 2/1, 3/0 or 1/2, "
            f"got {config.humans}/{config.ai}"
        )
    return config
