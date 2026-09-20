from pathlib import Path

from throwing_scale.presets import PresetStore, default_presets


def test_default_preset_is_long_frag_with_measured_points():
    presets = default_presets()
    assert [p.name for p in presets] == ["右手远投", "左手低抛", "威龙C4", "威龙大招", "红狼手炮"]
    pitches = [(p.pitch, p.distance_m) for p in presets[0].points]
    assert pitches[0] == (0.0, 21.0)
    assert pitches[1] == (1.0, 28.0)
    assert (19.0, 60.0) in pitches
    assert (32.5, 75.0) in pitches
    left = [(p.pitch, p.distance_m) for p in presets[1].points]
    assert (0.0, 9.0) in left
    assert (20.0, 24.0) in left
    assert (13.2, 19.0) in left
    assert (30.0, 30.0) in left
    assert presets[1].has_fuse is False
    assert presets[2].name == "威龙C4"
    assert presets[2].has_fuse is False
    assert (0.0, 9.0) in [(p.pitch, p.distance_m) for p in presets[2].points]
    assert (80.0, 1.0) in [(p.pitch, p.distance_m) for p in presets[2].points]
    ult = presets[3]
    assert ult.name == "威龙大招"
    assert ult.fuse_s == 3.0
    assert ult.can_cook is False
    assert ult.throw_delay_s == 0.0
    assert (14.0, 54.0) in [(p.pitch, p.distance_m) for p in ult.points]
    assert ult.instant_range_m == 70.0
    wolf = presets[4]
    assert wolf.name == "红狼手炮"
    assert wolf.fuse_s == 3.0
    assert wolf.instant_range_m == 82.0
    assert (17.8, 71.0) in [(p.pitch, p.distance_m) for p in wolf.points]
    assert (10.4, 33.0) in [(p.pitch, p.distance_m) for p in wolf.points]
    assert (23.7, 82.0) in [(p.pitch, p.distance_m) for p in wolf.points]


def test_roundtrip_json(tmp_path: Path):
    store = PresetStore(tmp_path / "presets.json")
    store.load_or_create()
    store.save()

    again = PresetStore(tmp_path / "presets.json")
    again.load_or_create()
    assert again.active_id == "frag_long"
    assert again.active().name == "右手远投"


def test_add_point_to_active(tmp_path: Path):
    store = PresetStore(tmp_path / "presets.json")
    store.load_or_create()
    store.add_point(pitch=20.0, distance_m=61.0)
    pitches = [p.pitch for p in store.active().points]
    assert 20.0 in pitches


def test_renames_old_name_and_adds_left_low(tmp_path: Path):
    path = tmp_path / "presets.json"
    path.write_text(
        '{"active_id":"frag_long","presets":[{"id":"frag_long","name":"手雷远抛","points":'
        '[{"pitch":0.0,"distance_m":21},{"pitch":1.0,"distance_m":28},{"pitch":19.0,"distance_m":60}]}]}',
        encoding="utf-8",
    )
    store = PresetStore(path)
    store.load_or_create()
    assert store.active().name == "右手远投"
    assert any(p.id == "left_low" and p.name == "左手低抛" for p in store.presets)


def test_old_four_points_gain_zero_and_one(tmp_path: Path):
    path = tmp_path / "presets.json"
    path.write_text(
        '{"active_id":"frag_long","presets":[{"id":"frag_long","name":"手雷远抛","points":'
        '[{"pitch":8.7,"distance_m":40}]}]}',
        encoding="utf-8",
    )
    store = PresetStore(path)
    store.load_or_create()
    pitches = {round(p.pitch, 1) for p in store.active().points}
    assert 0.0 in pitches
    assert 1.0 in pitches


def test_legacy_presets_are_migrated(tmp_path: Path):
    path = tmp_path / "presets.json"
    path.write_text(
        '{"active_id":"luna_frag","presets":[{"id":"luna_frag","name":"露娜手雷","points":[]}]}',
        encoding="utf-8",
    )
    store = PresetStore(path)
    store.load_or_create()
    assert store.active_id == "frag_long"
    assert store.active().name == "右手远投"
    assert any(p.id == "left_low" for p in store.presets)
