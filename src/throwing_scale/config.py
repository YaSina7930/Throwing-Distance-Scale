from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class OverlaySpec:
    visible: bool = True
    x: int = 280
    height_pct: int = 78
    preset_id: str = "frag_long"
    show_name: bool = True
    mirror: bool = False
    font_px: int = 13
    bg_opacity: int = 82
    text_opacity: int = 100


@dataclass
class InfoBoxSpec:
    visible: bool = True
    x: int = 40
    y: int = 80
    font_px: int = 22
    bg_opacity: int = 82
    text_opacity: int = 100
    show_a: bool = True
    show_b: bool = True


@dataclass
class AppConfig:
    counts_per_degree: float = 80.0
    invert_y: bool = False
    hotkey_zero_vk: int = 0x74
    hotkey_snap_vk: int = 0x75
    overlay_a: OverlaySpec = None  # type: ignore[assignment]
    overlay_b: OverlaySpec = None  # type: ignore[assignment]
    info_box: InfoBoxSpec = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.overlay_a is None:
            self.overlay_a = OverlaySpec(visible=True, x=280, height_pct=78)
        if self.overlay_b is None:
            self.overlay_b = OverlaySpec(visible=True, x=520, height_pct=78)
        if self.info_box is None:
            self.info_box = InfoBoxSpec()


def _spec_from(raw: object, fallback: OverlaySpec) -> OverlaySpec:
    if isinstance(raw, OverlaySpec):
        return raw
    data = asdict(fallback)
    if isinstance(raw, dict):
        data.update({k: v for k, v in raw.items() if k in data})
    return OverlaySpec(**data)


def _info_from(raw: object, fallback: InfoBoxSpec) -> InfoBoxSpec:
    if isinstance(raw, InfoBoxSpec):
        return raw
    data = asdict(fallback)
    if isinstance(raw, dict):
        data.update({k: v for k, v in raw.items() if k in data})
    return InfoBoxSpec(**data)


def load_config(path: Path) -> AppConfig:
    if not path.exists():
        return AppConfig()
    raw = json.loads(path.read_text(encoding="utf-8"))
    overlay_a = raw.get("overlay_a")
    overlay_b = raw.get("overlay_b")
    if overlay_a is None:
        overlay_a = OverlaySpec(
            visible=bool(raw.get("show_scale", True)),
            x=int(raw.get("overlay_x", 280)),
            height_pct=int(raw.get("overlay_height_pct", 78)),
            show_name=bool(raw.get("show_preset", True)),
        )
    if overlay_b is None:
        overlay_b = OverlaySpec(visible=True, x=520, height_pct=int(raw.get("overlay_height_pct", 78)))
    cfg = AppConfig(
        counts_per_degree=float(raw.get("counts_per_degree", 80.0)),
        invert_y=bool(raw.get("invert_y", False)),
        hotkey_zero_vk=int(raw.get("hotkey_zero_vk", 0x74)),
        hotkey_snap_vk=int(raw.get("hotkey_snap_vk", 0x75)),
        overlay_a=_spec_from(overlay_a, OverlaySpec(x=280)),
        overlay_b=_spec_from(overlay_b, OverlaySpec(x=520)),
        info_box=_info_from(raw.get("info_box"), InfoBoxSpec()),
    )
    return cfg


def save_config(path: Path, config: AppConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")
