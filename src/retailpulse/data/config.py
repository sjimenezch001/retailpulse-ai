"""Configuration paths are relative to the repository, not the current directory."""
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field


class Pilot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stores: list[str] = Field(default_factory=list)
    departments: list[str] = Field(default_factory=list)


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset_path: Path
    output_path: Path
    pilot: Pilot = Field(default_factory=Pilot)


def load_config(path: Path) -> tuple[Settings, Path]:
    path = path.resolve()
    settings = Settings.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    root = path.parent.parent
    for name in ("dataset_path", "output_path"):
        value = getattr(settings, name)
        resolved = (root / value).resolve()
        if value.is_absolute() or not resolved.is_relative_to(root):
            raise ValueError(f"{name} must be a relative path inside the repository")
        setattr(settings, name, resolved)
    if settings.dataset_path == settings.output_path:
        raise ValueError("Input and output paths must differ")
    return settings, root
