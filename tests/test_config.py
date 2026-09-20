from pathlib import Path

from throwing_scale.config import AppConfig, OverlaySpec, load_config, save_config


def test_load_missing_file_returns_two_overlays(tmp_path: Path):
    cfg = load_config(tmp_path / "missing.json")
    assert cfg.overlay_a.visible is True
    assert cfg.overlay_b.visible is True
    assert cfg.overlay_a.x != cfg.overlay_b.x


def test_config_roundtrip(tmp_path: Path):
    path = tmp_path / "config.json"
    original = AppConfig(
        counts_per_degree=120.5,
        invert_y=True,
        overlay_a=OverlaySpec(visible=True, x=40, height_pct=85, preset_id="frag_long"),
        overlay_b=OverlaySpec(visible=False, x=700, height_pct=60, preset_id="frag_long"),
    )
    save_config(path, original)
    loaded = load_config(path)
    assert loaded.overlay_a.x == 40
    assert loaded.overlay_b.visible is False
    assert loaded.overlay_b.height_pct == 60
    assert loaded.overlay_a.mirror is False
    assert loaded.info_box.visible is True
    assert loaded.info_box.show_a is True
    assert loaded.hotkey_snap_vk == 0x75


def test_migrates_old_single_overlay_keys(tmp_path: Path):
    path = tmp_path / "config.json"
    path.write_text(
        '{"counts_per_degree": 49.5, "overlay_x": 40, "overlay_height_pct": 85, "show_scale": true}',
        encoding="utf-8",
    )
    cfg = load_config(path)
    assert cfg.overlay_a.x == 40
    assert cfg.overlay_a.height_pct == 85
    assert cfg.overlay_b.x != 40
