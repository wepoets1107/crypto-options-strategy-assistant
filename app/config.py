from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT_DIR / "app" / "static"
DATA_DIR = ROOT_DIR / "data"
PORT = 8010
ENV_PATH = ROOT_DIR / ".env"
LLM_ENV_KEYS = ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL")


def read_env_file(path: Path | None = None) -> dict[str, str]:
    env_path = path or ENV_PATH
    values: dict[str, str] = {}
    if not env_path.exists():
        return values
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().lstrip("\ufeff")
        value = value.strip().strip('"').strip("'")
        values[key] = value
    return values


def load_dotenv(path: Path | None = None) -> None:
    for key, value in read_env_file(path).items():
        os.environ[key] = value


def write_llm_config(base_url: str, api_key: str, model: str, path: Path | None = None) -> None:
    env_path = path or ENV_PATH
    existing_lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    kept_lines = []
    for line in existing_lines:
        if "=" not in line:
            kept_lines.append(line)
            continue
        key = line.split("=", 1)[0].strip().lstrip("\ufeff")
        if key not in LLM_ENV_KEYS:
            kept_lines.append(line)
    values = {
        "LLM_BASE_URL": base_url.rstrip("/"),
        "LLM_API_KEY": api_key,
        "LLM_MODEL": model,
    }
    lines = kept_lines + [f"{key}={value}" for key, value in values.items()]
    env_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    for key, value in values.items():
        os.environ[key] = value


@dataclass(frozen=True)
class Settings:
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    llm_enabled: bool


def get_settings() -> Settings:
    load_dotenv()
    base_url = os.getenv("LLM_BASE_URL", "").rstrip("/")
    api_key = os.getenv("LLM_API_KEY", "")
    model = os.getenv("LLM_MODEL", "")
    return Settings(
        llm_base_url=base_url,
        llm_api_key=api_key,
        llm_model=model,
        llm_enabled=bool(base_url and api_key and model),
    )
