from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QTimer, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QMessageBox

from throwing_scale.ballistic import (
    MAX_DISPLAY_S,
    Fit,
    fit_throw,
    impact_at,
    timed_instant_grade,
    tick_distances,
)
from throwing_scale.config import OverlaySpec, load_config, save_config
from throwing_scale.control_window import ControlWindow
from throwing_scale.info_hud import DISTANCE, InfoHud
from throwing_scale.limits import LOOK_UP_MAX
from throwing_scale.overlay_window import OverlayWindow, _time_color, instant_color
from throwing_scale.pitch import PitchTracker
from throwing_scale.presets import Preset, PresetStore
from throwing_scale.win_input import (
    HOTKEY_SNAP,
    HOTKEY_ZERO,
    NativeFilter,
    register_hotkeys,
    register_raw_mouse,
    unregister_hotkeys,
)


def data_dir() -> Path:
    if getattr(sys, "frozen", False):
        root = Path(sys.executable).parent
        bundled = Path(getattr(sys, "_MEIPASS", root)) / "data" / "presets.json"
    else:
        root = Path(__file__).resolve().parents[2]
        bundled = root / "data" / "presets.json"
    path = root / "data"
    path.mkdir(parents=True, exist_ok=True)
    dest = path / "presets.json"
    if bundled.exists() and not dest.exists():
        dest.write_bytes(bundled.read_bytes())
    return path


class ScaleApp(QObject):
    def __init__(self) -> None:
        super().__init__()
        self._config_path = data_dir() / "config.json"
        self.cfg = load_config(self._config_path)
        self.tracker = PitchTracker(
            counts_per_degree=self.cfg.counts_per_degree,
            invert_y=self.cfg.invert_y,
        )
        self.store = PresetStore(data_dir() / "presets.json")
        self.store.load_or_create()
        self.control = ControlWindow()
        self.overlays = [OverlayWindow(), OverlayWindow()]
        self.info = InfoHud()
        self._filter = None
        self._fits: dict[str, Fit | None] = {}
        self._dirty = True
        self._frame = QTimer(self)
        self._frame.setTimerType(Qt.TimerType.PreciseTimer)
        self._frame.setInterval(16)
        self._frame.timeout.connect(self._on_frame)
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._flush_config)
        self._bind()

    def _bind(self) -> None:
        self.control.zero_requested.connect(self.on_zero)
        self.control.snap90_requested.connect(self.on_snap90)
        self.control.invert_changed.connect(self.on_invert)
        self.control.sensitivity_changed.connect(self.on_sensitivity)
        self.control.overlay_changed.connect(self.on_overlay_changed)
        self.control.info_changed.connect(self.on_info_changed)
        self.control.hotkey_changed.connect(self.on_hotkeys_changed)
        self.control.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.control.destroyed.connect(self._on_control_closed)

    def start(self) -> None:
        self.control.fill_presets(self.store.presets, self.cfg.overlay_a, self.cfg.overlay_b)
        self.control.apply_config(self.cfg)
        self.control.show()
        self._place_all()
        hwnd = int(self.control.winId())
        try:
            register_raw_mouse(hwnd)
        except OSError as exc:
            QMessageBox.critical(self.control, "鼠标输入注册失败", str(exc))
        self._bind_hotkeys()
        self._filter = NativeFilter(self.on_mouse, self.on_hotkey)
        QApplication.instance().installNativeEventFilter(self._filter.qt_filter())
        self._sync()
        self._frame.start()

    def _persist(self) -> None:
        self._save_timer.start(250)

    def _flush_config(self) -> None:
        save_config(self._config_path, self.cfg)

    def _spec(self, index: int) -> OverlaySpec:
        return self.cfg.overlay_a if index == 0 else self.cfg.overlay_b

    def _set_spec(self, index: int, spec: OverlaySpec) -> None:
        if index == 0:
            self.cfg.overlay_a = spec
        else:
            self.cfg.overlay_b = spec

    def _preset(self, preset_id: str) -> Preset:
        for preset in self.store.presets:
            if preset.id == preset_id:
                return preset
        return self.store.active()

    def _fit_for(self, preset: Preset) -> Fit | None:
        if preset.id not in self._fits:
            if preset.instant_range_m:
                self._fits[preset.id] = fit_throw(
                    preset.points,
                    delay=0.0,
                    range_time_anchors=((preset.instant_range_m, 3.0),),
                )
            else:
                self._fits[preset.id] = fit_throw(preset.points)
        return self._fits[preset.id]

    def _place_one(self, index: int) -> None:
        spec = self._spec(index)
        screen = QGuiApplication.primaryScreen().availableGeometry()
        overlay = self.overlays[index]
        overlay.place(screen, spec.x, spec.height_pct)
        overlay.setVisible(spec.visible)

    def _place_all(self) -> None:
        self._place_one(0)
        self._place_one(1)

    def _sync_one(self, index: int) -> None:
        spec = self._spec(index)
        preset = self._preset(spec.preset_id)
        fit = self._fit_for(preset)
        delay = preset.throw_delay_s
        use_offset = True
        timed = bool(preset.has_fuse and not preset.can_cook)
        max_boom = MAX_DISPLAY_S if timed else None
        instant_max_range = preset.instant_range_m
        instant_max_pitch = 45.0 if preset.instant_range_m else None
        labels = (
            tick_distances(
                fit,
                delay=delay,
                use_offset=use_offset,
                fuse_s=preset.fuse_s,
                max_boom=max_boom,
                instant_max_range=instant_max_range,
                instant_max_pitch=instant_max_pitch,
                step=5.0,
            )
            if fit
            else []
        )
        hit = impact_at(self.tracker.pitch, fit, delay=delay, use_offset=use_offset) if fit else None
        if hit and max_boom is not None and hit[1] > max_boom:
            hit = None
        current = hit[0] if hit else None
        cook = hit[1] if hit else None
        grade = (
            timed_instant_grade(hit[1], preset.fuse_s)
            if hit and preset.fuse_s is not None and not preset.can_cook
            else None
        )
        if grade and instant_max_range is not None and current is not None and current > instant_max_range + 0.6:
            grade = None
        if grade and instant_max_pitch is not None and self.tracker.pitch > instant_max_pitch:
            grade = None
        self.overlays[index].set_state(
            self.tracker.pitch,
            preset.name,
            preset.points,
            tick_labels=labels,
            current_distance=current,
            current_cook=cook,
            current_grade=grade,
            show_scale=spec.visible,
            show_preset=spec.show_name,
            mirror=spec.mirror,
            font_px=spec.font_px,
            bg_opacity=spec.bg_opacity,
            text_opacity=spec.text_opacity,
            show_time=bool(preset.has_fuse and preset.can_cook),
            show_instant=bool(preset.has_fuse and not preset.can_cook),
        )
        self.overlays[index].setVisible(spec.visible)

    def _sync_info(self) -> None:
        box = self.cfg.info_box
        lines: list[tuple[str, object]] = []
        flags = (box.show_a, box.show_b)
        for index in (0, 1):
            if not flags[index]:
                continue
            spec = self._spec(index)
            preset = self._preset(spec.preset_id)
            fit = self._fit_for(preset)
            hit = (
                impact_at(
                    self.tracker.pitch,
                    fit,
                    delay=preset.throw_delay_s,
                    use_offset=True,
                )
                if fit
                else None
            )
            if hit is None:
                lines.append((f"{preset.name}  --", DISTANCE))
            elif preset.has_fuse and not preset.can_cook and hit[1] > MAX_DISPLAY_S:
                lines.append((f"{preset.name}  --", DISTANCE))
            elif preset.has_fuse and preset.can_cook:
                lines.append((f"{preset.name}  {hit[0]:.0f}m  {hit[1]:.1f}s", _time_color(hit[1])))
            elif preset.has_fuse and not preset.can_cook and preset.fuse_s is not None:
                grade = timed_instant_grade(hit[1], preset.fuse_s)
                if grade and preset.instant_range_m is not None and hit[0] > preset.instant_range_m + 0.6:
                    grade = None
                if grade and preset.instant_range_m is not None and self.tracker.pitch > 45.0:
                    grade = None
                if grade:
                    lines.append((f"{preset.name}  {hit[0]:.0f}m 瞬", instant_color(grade)))
                else:
                    lines.append((f"{preset.name}  {hit[0]:.0f}m", DISTANCE))
            else:
                lines.append((f"{preset.name}  {hit[0]:.0f}m", DISTANCE))
        self.info.set_lines(
            lines,
            box.font_px,
            box.bg_opacity,
            box.text_opacity,
            pitch=self.tracker.pitch,
        )
        self.info.place(box.x, box.y)
        self.info.setVisible(box.visible)

    def _sync(self) -> None:
        self._sync_one(0)
        self._sync_one(1)
        self._sync_info()
        self.control.set_pitch(self.tracker.pitch)

    def _on_frame(self) -> None:
        if not self._dirty:
            return
        self._dirty = False
        self._sync()

    def _on_control_closed(self) -> None:
        self._frame.stop()
        self._flush_config()
        for overlay in self.overlays:
            overlay.close()
        self.info.close()
        try:
            unregister_hotkeys(int(self.control.winId()))
        except Exception:
            pass

    @Slot(int, int)
    def on_mouse(self, dx: int, dy: int) -> None:
        self.tracker.add_raw_delta(dx, dy)
        self._dirty = True

    @Slot(int)
    def on_hotkey(self, hotkey_id: int) -> None:
        if hotkey_id == HOTKEY_ZERO:
            self.on_zero()
        elif hotkey_id == HOTKEY_SNAP:
            self.on_snap90()

    @Slot()
    def on_zero(self) -> None:
        self.tracker.snap_to(0.0)
        self.control.set_status("已对准平视 0°。")
        self._dirty = True
        self._sync()

    @Slot()
    def on_snap90(self) -> None:
        self.tracker.snap_to(LOOK_UP_MAX)
        self.control.set_status("已对准抬头最高 +80°。")
        self._dirty = True
        self._sync()

    @Slot()
    def on_hotkeys_changed(self) -> None:
        zero = int(self.control.zero_key.currentData() or 0x74)
        snap = int(self.control.snap_key.currentData() or 0x75)
        if zero == snap:
            self.control.set_status("两个热键不能相同。")
            return
        self.cfg.hotkey_zero_vk = zero
        self.cfg.hotkey_snap_vk = snap
        self._persist()
        self._bind_hotkeys()

    def _bind_hotkeys(self) -> None:
        hwnd = int(self.control.winId())
        unregister_hotkeys(hwnd)
        bound, failed = register_hotkeys(hwnd, self.cfg.hotkey_zero_vk, self.cfg.hotkey_snap_vk)
        if failed:
            self.control.set_status("热键未全部注册：" + "、".join(failed) + "。仍可用窗口按钮。")
        elif bound:
            names = " / ".join(label for _hid, _vk, label in bound)
            self.control.set_status(f"热键已就绪：{names}")

    @Slot(bool)
    def on_invert(self, checked: bool) -> None:
        self.tracker.invert_y = checked
        self.cfg.invert_y = checked
        self._persist()

    @Slot(float)
    def on_sensitivity(self, value: float) -> None:
        self.tracker.set_counts_per_degree(value)
        self.cfg.counts_per_degree = float(value)
        self._persist()
        self._sync()

    @Slot(int)
    def on_overlay_changed(self, index: int) -> None:
        slot = self.control.slot_a if index == 0 else self.control.slot_b
        self._set_spec(index, slot.spec())
        self._place_one(index)
        self._persist()
        self._sync_one(index)
        self._sync_info()

    @Slot()
    def on_info_changed(self) -> None:
        self.cfg.info_box = self.control.info_spec()
        self._persist()
        self._sync_info()


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    scale = ScaleApp()
    scale.start()
    return app.exec()
