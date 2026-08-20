"""键位表：动作 ↔ Qt Key 映射，缺文件/坏 JSON 回落默认。"""
from __future__ import annotations
import json
from pathlib import Path

from PySide6.QtCore import Qt

from .._paths import user_dir

# 动作→Qt Key 名，去 Key_ 前缀；grab/throw 预留
DEFAULT_KEYBINDS = {
    "left": "A", "right": "D", "up": "W", "down": "S",
    "jump": "Space", "grab": "K", "throw": "J",
}
ACTIONS = tuple(DEFAULT_KEYBINDS)
MOVEMENT_ACTIONS = ("left", "right", "up", "down", "jump")


def _default_path() -> Path:
    return user_dir() / "keybinds.json"


def _to_qt_key(name: str) -> int | None:
    """键名 → Qt Key 整数值；未知键名 None。"""
    key = getattr(Qt.Key, "Key_" + name, None)
    return None if key is None else int(key)


def key_name_from_qt(key: int) -> str | None:
    """Qt Key 整数值 → 键名（去 Key_ 前缀）。"""
    try:
        name = Qt.Key(int(key)).name
    except ValueError:
        return None
    if not name.startswith("Key_"):
        return None
    return name[4:]


def load_key_names(path=None) -> dict[str, str]:
    """动作→键名表，缺文件/坏 JSON 回落默认。"""
    p = Path(path) if path is not None else _default_path()
    names = dict(DEFAULT_KEYBINDS)
    if not p.exists():
        try:
            p.write_text(json.dumps(DEFAULT_KEYBINDS, indent=2), encoding="utf-8")
        except Exception:
            pass
        return names
    try:
        loaded = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return names
    if isinstance(loaded, dict):
        for action in ACTIONS:
            v = loaded.get(action)
            if isinstance(v, str) and _to_qt_key(v) is not None:
                names[action] = v
    return names


def save_key_names(names: dict[str, str], path=None) -> dict[str, str]:
    """保存有效键名；未知/缺失动作回落默认。"""
    p = Path(path) if path is not None else _default_path()
    clean = dict(DEFAULT_KEYBINDS)
    for action in ACTIONS:
        v = names.get(action)
        if isinstance(v, str) and _to_qt_key(v) is not None:
            clean[action] = v
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(clean, indent=2), encoding="utf-8")
    except Exception:
        pass
    return clean


def load_keymap(path=None) -> dict[str, int]:
    """动作 → Qt Key 整数值表（HUD current_input 用）。"""
    names = load_key_names(path)
    return {action: _to_qt_key(name) for action, name in names.items()}


def key_display_name(action, names=None) -> str:
    """动作的键名显示串（HUD 键位表用）；names 传入省重读文件。"""
    if names is None:
        names = load_key_names()
    return names.get(action, DEFAULT_KEYBINDS.get(action, ""))
