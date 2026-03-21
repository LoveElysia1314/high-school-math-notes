from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from .constants import PRESET_CONFIGS, PRESETS_FILE


class ConfigManager:
    def __init__(self, preset_file: str = PRESETS_FILE):
        self.preset_file = preset_file
        self.presets: Dict[str, Dict] = {}
        self.builtin_presets = dict(PRESET_CONFIGS)
        self.load_presets()

    def load_presets(self) -> None:
        loaded = {}
        if Path(self.preset_file).exists():
            try:
                with open(self.preset_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
            except Exception:
                loaded = {}

        self.presets = dict(self.builtin_presets)
        if isinstance(loaded, dict):
            for k, v in loaded.items():
                if k == "__last_preset_name__":
                    continue
                if isinstance(v, dict):
                    self.presets[k] = v

            last = loaded.get("__last_preset_name__")
            if isinstance(last, str) and last in self.presets:
                self.presets["__last_preset_name__"] = last

    def save_presets(self) -> None:
        with open(self.preset_file, "w", encoding="utf-8") as f:
            json.dump(self.presets, f, indent=2, ensure_ascii=False)

    def get_preset_names(self) -> List[str]:
        return sorted([k for k in self.presets.keys() if k != "__last_preset_name__"])

    def get_preset(self, name: str) -> Optional[Dict]:
        return self.presets.get(name)

    def create_preset(self, name: str, config: Dict) -> bool:
        if name in self.presets:
            return False
        self.presets[name] = config
        self.save_presets()
        return True

    def override_preset(self, name: str, config: Dict) -> None:
        self.presets[name] = config
        self.save_presets()

    def delete_preset(self, name: str) -> bool:
        if name in self.builtin_presets or name not in self.presets:
            return False
        del self.presets[name]
        self.save_presets()
        return True

    def reset_to_builtin(self) -> None:
        self.presets = dict(self.builtin_presets)
        self.save_presets()

    def is_builtin(self, name: str) -> bool:
        return name in self.builtin_presets

    def get_last_preset(self) -> Optional[str]:
        last_name = self.presets.get("__last_preset_name__")
        if (
            last_name
            and last_name in self.presets
            and last_name != "__last_preset_name__"
        ):
            return last_name
        return None

    def set_last_preset(self, name: str) -> None:
        if name in self.presets and name != "__last_preset_name__":
            self.presets["__last_preset_name__"] = name
            self.save_presets()
