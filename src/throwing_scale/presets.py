from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class DistancePoint:
    pitch: float
    distance_m: float


@dataclass
class Preset:
    id: str
    name: str
    points: list[DistancePoint] = field(default_factory=list)
    has_fuse: bool = True
    fuse_s: float | None = 5.0
    throw_delay_s: float = 0.2
    can_cook: bool = True
    instant_range_m: float | None = None


LEGACY_IDS = {"luna_frag", "luna_arrow", "wolf_smoke"}

LONG_THROW_POINTS = [
    DistancePoint(0.0, 21.0),
    DistancePoint(1.0, 28.0),
    DistancePoint(8.7, 40.0),
    DistancePoint(14.0, 50.0),
    DistancePoint(19.0, 60.0),
    DistancePoint(25.0, 70.0),
    DistancePoint(32.5, 75.0),
]

LEFT_LOW_POINTS = [
    DistancePoint(0.0, 9.0),
    DistancePoint(13.2, 19.0),
    DistancePoint(20.0, 24.0),
    DistancePoint(30.0, 30.0),
]

C4_POINTS = [
    DistancePoint(0.0, 9.0),
    DistancePoint(8.0, 12.0),
    DistancePoint(26.0, 18.0),
    DistancePoint(80.0, 1.0),
]

ULT_POINTS = [
    DistancePoint(0.0, 20.0),
    DistancePoint(8.0, 39.0),
    DistancePoint(11.0, 46.0),
    DistancePoint(14.0, 54.0),
]

WOLF_CANNON_POINTS = [
    DistancePoint(0.0, 19.0),
    DistancePoint(10.4, 33.0),
    DistancePoint(17.8, 71.0),
    DistancePoint(23.7, 82.0),
]

NO_FUSE_IDS = {"left_low", "weidong_c4"}
TIMED_BURST_IDS = {"weidong_ult", "honglang_cannon"}


def default_presets() -> list[Preset]:
    return [
        Preset(id="frag_long", name="右手远投", points=list(LONG_THROW_POINTS), has_fuse=True, fuse_s=5.0, throw_delay_s=0.2, can_cook=True),
        Preset(id="left_low", name="左手低抛", points=list(LEFT_LOW_POINTS), has_fuse=False, fuse_s=None, throw_delay_s=0.0, can_cook=False),
        Preset(id="weidong_c4", name="威龙C4", points=list(C4_POINTS), has_fuse=False, fuse_s=None, throw_delay_s=0.0, can_cook=False),
        Preset(id="weidong_ult", name="威龙大招", points=list(ULT_POINTS), has_fuse=True, fuse_s=3.0, throw_delay_s=0.0, can_cook=False, instant_range_m=70.0),
        Preset(id="honglang_cannon", name="红狼手炮", points=list(WOLF_CANNON_POINTS), has_fuse=True, fuse_s=3.0, throw_delay_s=0.0, can_cook=False, instant_range_m=82.0),
    ]


class PresetStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.presets: list[Preset] = []
        self.active_id: str = "frag_long"

    def load_or_create(self) -> None:
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.presets = [
                Preset(
                    id=item["id"],
                    name=item["name"],
                    points=[DistancePoint(**pt) for pt in item.get("points", [])],
                    has_fuse=bool(item.get("has_fuse", item["id"] not in NO_FUSE_IDS)),
                    fuse_s=item.get("fuse_s", 5.0 if item["id"] == "frag_long" else (3.0 if item["id"] in TIMED_BURST_IDS else None)),
                    throw_delay_s=float(item.get("throw_delay_s", 0.2 if item["id"] == "frag_long" else 0.0)),
                    can_cook=bool(item.get("can_cook", item["id"] == "frag_long")),
                    instant_range_m=item.get("instant_range_m", { "weidong_ult": 70.0, "honglang_cannon": 82.0 }.get(item["id"])),
                )
                for item in data.get("presets", [])
            ]
            self.active_id = data.get("active_id", self.presets[0].id if self.presets else "frag_long")
            if not self.presets or self._legacy():
                self.presets = default_presets()
                self.active_id = self.presets[0].id
                self.save()
            else:
                self._sync_presets()
            return
        self.presets = default_presets()
        self.active_id = self.presets[0].id
        self.save()

    def _legacy(self) -> bool:
        ids = {p.id for p in self.presets}
        return bool(ids & LEGACY_IDS) and "frag_long" not in ids

    def _sync_presets(self) -> None:
        changed = False
        ids = {p.id for p in self.presets}
        for preset in self.presets:
            if preset.id == "frag_long":
                if preset.name == "手雷远抛":
                    preset.name = "右手远投"
                    changed = True
                pitches = {round(pt.pitch, 1) for pt in preset.points}
                if {0.0, 1.0, 19.0} - pitches:
                    preset.points = list(LONG_THROW_POINTS)
                    changed = True
        specs = (
            ("left_low", "左手低抛", LEFT_LOW_POINTS, False, None, 0.0, False, None, {0.0, 13.2, 20.0, 30.0}),
            ("weidong_c4", "威龙C4", C4_POINTS, False, None, 0.0, False, None, {0.0, 8.0, 26.0, 80.0}),
            ("weidong_ult", "威龙大招", ULT_POINTS, True, 3.0, 0.0, False, 70.0, {0.0, 8.0, 11.0, 14.0}),
            ("honglang_cannon", "红狼手炮", WOLF_CANNON_POINTS, True, 3.0, 0.0, False, 82.0, {0.0, 10.4, 17.8, 23.7}),
        )
        for pid, name, points, has_fuse, fuse_s, delay, can_cook, instant_range, need in specs:
            if pid not in ids:
                self.presets.append(
                    Preset(
                        id=pid,
                        name=name,
                        points=list(points),
                        has_fuse=has_fuse,
                        fuse_s=fuse_s,
                        throw_delay_s=delay,
                        can_cook=can_cook,
                        instant_range_m=instant_range,
                    )
                )
                changed = True
                continue
            for preset in self.presets:
                if preset.id != pid:
                    continue
                if (
                    preset.has_fuse != has_fuse
                    or preset.fuse_s != fuse_s
                    or preset.throw_delay_s != delay
                    or preset.can_cook != can_cook
                    or preset.instant_range_m != instant_range
                ):
                    preset.has_fuse = has_fuse
                    preset.fuse_s = fuse_s
                    preset.throw_delay_s = delay
                    preset.can_cook = can_cook
                    preset.instant_range_m = instant_range
                    changed = True
                pitches = {round(pt.pitch, 1) for pt in preset.points}
                if need - pitches:
                    preset.points = list(points)
                    changed = True
        if changed:
            self.save()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "active_id": self.active_id,
            "presets": [
                {
                    "id": p.id,
                    "name": p.name,
                    "has_fuse": p.has_fuse,
                    "fuse_s": p.fuse_s,
                    "throw_delay_s": p.throw_delay_s,
                    "can_cook": p.can_cook,
                    "instant_range_m": p.instant_range_m,
                    "points": [asdict(pt) for pt in p.points],
                }
                for p in self.presets
            ],
        }
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def active(self) -> Preset:
        for preset in self.presets:
            if preset.id == self.active_id:
                return preset
        return self.presets[0]

    def set_active(self, preset_id: str) -> None:
        ids = {p.id for p in self.presets}
        if preset_id not in ids:
            raise KeyError(preset_id)
        self.active_id = preset_id

    def add_point(self, pitch: float, distance_m: float) -> None:
        self.active().points.append(DistancePoint(pitch=float(pitch), distance_m=float(distance_m)))
        self.active().points.sort(key=lambda pt: pt.pitch)
