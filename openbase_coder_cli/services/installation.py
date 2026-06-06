from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from openbase_coder_cli.paths import INSTALLATION_JSON_PATH


@dataclass
class InstallationConfig:
    workspace_path: str
    env_file: str

    def save(self) -> None:
        INSTALLATION_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        INSTALLATION_JSON_PATH.write_text(json.dumps(asdict(self), indent=2) + "\n")

    @classmethod
    def load(cls) -> InstallationConfig:
        data = json.loads(INSTALLATION_JSON_PATH.read_text())
        return cls(**data)

    @classmethod
    def exists(cls) -> bool:
        return INSTALLATION_JSON_PATH.is_file()
