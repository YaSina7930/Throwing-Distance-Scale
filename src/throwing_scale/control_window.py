from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from throwing_scale.config import InfoBoxSpec, OverlaySpec
from throwing_scale.presets import Preset
from throwing_scale.win_input import FUNCTION_KEYS, VK_F5, VK_F6


class OverlaySlot(QGroupBox):
    changed = Signal()

    def __init__(self, title: str) -> None:
        super().__init__(title)
        self.visible_box = QCheckBox("显示标尺")
        self.visible_box.setChecked(True)
        self.name_box = QCheckBox("显示名称")
        self.name_box.setChecked(True)
        self.mirror_box = QCheckBox("左右镜像")
        self.preset_combo = QComboBox()
        self.x_slider = QSlider(Qt.Orientation.Horizontal)
        self.x_slider.setRange(0, 4000)
        self.x_slider.setValue(280)
        self.height_slider = QSlider(Qt.Orientation.Horizontal)
        self.height_slider.setRange(10, 100)
        self.height_slider.setValue(78)
        self.font_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_slider.setRange(8, 36)
        self.font_slider.setValue(13)

        form = QFormLayout(self)
        vis = QHBoxLayout()
        vis.addWidget(self.visible_box)
        vis.addWidget(self.name_box)
        vis.addWidget(self.mirror_box)
        form.addRow(vis)
        form.addRow("预设", self.preset_combo)
        form.addRow("水平位置", self.x_slider)
        form.addRow("垂直高度", self.height_slider)
        form.addRow("文字大小", self.font_slider)
        self.bg_slider = QSlider(Qt.Orientation.Horizontal)
        self.bg_slider.setRange(0, 100)
        self.bg_slider.setValue(82)
        self.text_slider = QSlider(Qt.Orientation.Horizontal)
        self.text_slider.setRange(0, 100)
        self.text_slider.setValue(100)
        form.addRow("背景透明度", self.bg_slider)
        form.addRow("文字透明度", self.text_slider)

        self.visible_box.toggled.connect(self.changed)
        self.name_box.toggled.connect(self.changed)
        self.mirror_box.toggled.connect(self.changed)
        self.preset_combo.currentIndexChanged.connect(self.changed)
        self.x_slider.valueChanged.connect(self.changed)
        self.height_slider.valueChanged.connect(self.changed)
        self.font_slider.valueChanged.connect(self.changed)
        self.bg_slider.valueChanged.connect(self.changed)
        self.text_slider.valueChanged.connect(self.changed)

    def fill_presets(self, presets: list[Preset], active_id: str) -> None:
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        index = 0
        for i, preset in enumerate(presets):
            self.preset_combo.addItem(preset.name, preset.id)
            if preset.id == active_id:
                index = i
        self.preset_combo.setCurrentIndex(index)
        self.preset_combo.blockSignals(False)

    def spec(self) -> OverlaySpec:
        preset_id = self.preset_combo.currentData() or "frag_long"
        return OverlaySpec(
            visible=self.visible_box.isChecked(),
            x=int(self.x_slider.value()),
            height_pct=int(self.height_slider.value()),
            preset_id=str(preset_id),
            show_name=self.name_box.isChecked(),
            mirror=self.mirror_box.isChecked(),
            font_px=int(self.font_slider.value()),
            bg_opacity=int(self.bg_slider.value()),
            text_opacity=int(self.text_slider.value()),
        )

    def apply(self, spec: OverlaySpec) -> None:
        widgets = (
            self.visible_box,
            self.name_box,
            self.mirror_box,
            self.preset_combo,
            self.x_slider,
            self.height_slider,
            self.font_slider,
            self.bg_slider,
            self.text_slider,
        )
        for widget in widgets:
            widget.blockSignals(True)
        self.visible_box.setChecked(spec.visible)
        self.name_box.setChecked(spec.show_name)
        self.mirror_box.setChecked(spec.mirror)
        self.x_slider.setValue(int(spec.x))
        self.height_slider.setValue(int(spec.height_pct))
        self.font_slider.setValue(int(spec.font_px))
        self.bg_slider.setValue(int(spec.bg_opacity))
        self.text_slider.setValue(int(spec.text_opacity))
        for i in range(self.preset_combo.count()):
            if self.preset_combo.itemData(i) == spec.preset_id:
                self.preset_combo.setCurrentIndex(i)
                break
        for widget in widgets:
            widget.blockSignals(False)


def _fill_fkey_combo(box: QComboBox, current_vk: int) -> None:
    box.blockSignals(True)
    box.clear()
    index = 0
    for i, (name, vk) in enumerate(FUNCTION_KEYS):
        box.addItem(name, vk)
        if vk == current_vk:
            index = i
    box.setCurrentIndex(index)
    box.blockSignals(False)


class ControlWindow(QMainWindow):
    zero_requested = Signal()
    snap90_requested = Signal()
    invert_changed = Signal(bool)
    sensitivity_changed = Signal(float)
    overlay_changed = Signal(int)
    info_changed = Signal()
    hotkey_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("投掷距离标尺")
        self.setMinimumWidth(520)
        self.resize(560, 560)

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setSpacing(10)

        self.pitch_label = QLabel("P:+0.0°")
        self.pitch_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pitch_label.setStyleSheet(
            "font: 700 32px Consolas; color: #5dff6a; background: #101410; padding: 12px; border-radius: 8px;"
        )
        layout.addWidget(self.pitch_label)

        self.status_label = QLabel("两个标尺可同时显示，位置/高度/预设分开设。")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        form = QFormLayout()
        self.sensitivity = QDoubleSpinBox()
        self.sensitivity.setRange(1.0, 2000.0)
        self.sensitivity.setDecimals(1)
        self.sensitivity.setSingleStep(1.0)
        self.sensitivity.setValue(80.0)
        self.sensitivity.setSuffix(" 计数/°")
        self.sensitivity.valueChanged.connect(self.sensitivity_changed.emit)
        form.addRow("浮标跟随", self.sensitivity)

        self.zero_key = QComboBox()
        self.snap_key = QComboBox()
        _fill_fkey_combo(self.zero_key, VK_F5)
        _fill_fkey_combo(self.snap_key, VK_F6)
        self.zero_key.currentIndexChanged.connect(self._emit_hotkey)
        self.snap_key.currentIndexChanged.connect(self._emit_hotkey)
        form.addRow("平视 0° 热键", self.zero_key)
        form.addRow("抬头 80° 热键", self.snap_key)

        self.invert = QCheckBox("反转鼠标 Y")
        self.invert.toggled.connect(self.invert_changed.emit)
        form.addRow("", self.invert)
        layout.addLayout(form)

        slots = QHBoxLayout()
        self.slot_a = OverlaySlot("标尺 A")
        self.slot_b = OverlaySlot("标尺 B")
        self.slot_a.changed.connect(lambda: self.overlay_changed.emit(0))
        self.slot_b.changed.connect(lambda: self.overlay_changed.emit(1))
        slots.addWidget(self.slot_a)
        slots.addWidget(self.slot_b)
        layout.addLayout(slots)

        info = QGroupBox("绿标信息框")
        info_form = QFormLayout(info)
        self.info_visible = QCheckBox("显示")
        self.info_visible.setChecked(True)
        self.info_x = QSlider(Qt.Orientation.Horizontal)
        self.info_x.setRange(0, 4000)
        self.info_x.setValue(40)
        self.info_y = QSlider(Qt.Orientation.Horizontal)
        self.info_y.setRange(0, 2200)
        self.info_y.setValue(80)
        self.info_font = QSlider(Qt.Orientation.Horizontal)
        self.info_font.setRange(12, 48)
        self.info_font.setValue(22)
        self.info_show_a = QCheckBox("显示标尺 A")
        self.info_show_a.setChecked(True)
        self.info_show_b = QCheckBox("显示标尺 B")
        self.info_show_b.setChecked(True)
        info_show = QHBoxLayout()
        info_show.addWidget(self.info_visible)
        info_show.addWidget(self.info_show_a)
        info_show.addWidget(self.info_show_b)
        info_form.addRow(info_show)
        info_form.addRow("水平位置", self.info_x)
        info_form.addRow("垂直位置", self.info_y)
        info_form.addRow("文字大小", self.info_font)
        self.info_bg = QSlider(Qt.Orientation.Horizontal)
        self.info_bg.setRange(0, 100)
        self.info_bg.setValue(82)
        self.info_text = QSlider(Qt.Orientation.Horizontal)
        self.info_text.setRange(0, 100)
        self.info_text.setValue(100)
        info_form.addRow("背景透明度", self.info_bg)
        info_form.addRow("文字透明度", self.info_text)
        self.info_visible.toggled.connect(self.info_changed)
        self.info_x.valueChanged.connect(self.info_changed)
        self.info_y.valueChanged.connect(self.info_changed)
        self.info_font.valueChanged.connect(self.info_changed)
        self.info_bg.valueChanged.connect(self.info_changed)
        self.info_text.valueChanged.connect(self.info_changed)
        self.info_show_a.toggled.connect(self.info_changed)
        self.info_show_b.toggled.connect(self.info_changed)
        layout.addWidget(info)

        buttons = QHBoxLayout()
        self.zero_btn = QPushButton("平视 0°")
        self.zero_btn.clicked.connect(self.zero_requested.emit)
        self.snap_prone_btn = QPushButton("抬头 80°")
        self.snap_prone_btn.clicked.connect(self.snap90_requested.emit)
        buttons.addWidget(self.zero_btn)
        buttons.addWidget(self.snap_prone_btn)
        layout.addLayout(buttons)

        hint = QLabel(
            "标尺秒数 = 游戏爆炸剩余时间应对值（飞行 + 0.2 秒出手）。\n"
            "浮标跟随直接微调。信息框里的标尺 A/B 与标尺本体显隐无关。"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #9aa89a;")
        layout.addWidget(hint)

        roles = QLabel(
            "右手远投适用角色：蛊，牧羊人，乌鲁鲁，液氮，露娜\n"
            "左手低抛使用角色：红狼，风衣，旅人\n"
            "爆为瞬爆"
        )
        roles.setWordWrap(True)
        roles.setStyleSheet("color: #c8dcc8; padding: 8px 0 4px 0;")
        layout.addWidget(roles)
        layout.addStretch()

        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #1a1f1c; color: #e8eee8; }
            QGroupBox { color: #e8eee8; border: 1px solid #3a4a3c; margin-top: 8px; padding: 8px; }
            QLabel { color: #e8eee8; }
            QComboBox, QDoubleSpinBox {
                background: #101410; color: #e8eee8; border: 1px solid #3a4a3c; padding: 4px;
            }
            QPushButton {
                background: #2a3a2e; color: #e8eee8; border: 1px solid #4a6a50; padding: 8px;
            }
            QPushButton:hover { background: #345038; }
            QSlider::groove:horizontal { height: 6px; background: #2a3a2e; }
            QSlider::handle:horizontal { width: 14px; background: #5dff6a; margin: -5px 0; }
            """
        )

    def fill_presets(self, presets: list[Preset], spec_a: OverlaySpec, spec_b: OverlaySpec) -> None:
        self.slot_a.fill_presets(presets, spec_a.preset_id)
        self.slot_b.fill_presets(presets, spec_b.preset_id)

    def set_pitch(self, pitch: float) -> None:
        self.pitch_label.setText(f"P:{pitch:+.1f}°")

    def set_sensitivity(self, value: float) -> None:
        self.sensitivity.blockSignals(True)
        self.sensitivity.setValue(float(value))
        self.sensitivity.blockSignals(False)

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def _emit_hotkey(self) -> None:
        self.set_hotkey_button_labels()
        self.hotkey_changed.emit()

    def set_hotkey_button_labels(self) -> None:
        zero = self.zero_key.currentText() or "F5"
        snap = self.snap_key.currentText() or "F6"
        self.zero_btn.setText(f"{zero} 平视 0°")
        self.snap_prone_btn.setText(f"{snap} 抬头 80°")

    def apply_config(self, cfg) -> None:
        self.invert.blockSignals(True)
        self.invert.setChecked(cfg.invert_y)
        self.invert.blockSignals(False)
        self.set_sensitivity(cfg.counts_per_degree)
        _fill_fkey_combo(self.zero_key, cfg.hotkey_zero_vk)
        _fill_fkey_combo(self.snap_key, cfg.hotkey_snap_vk)
        self.set_hotkey_button_labels()
        self.slot_a.apply(cfg.overlay_a)
        self.slot_b.apply(cfg.overlay_b)
        box = cfg.info_box
        widgets = (
            self.info_visible,
            self.info_x,
            self.info_y,
            self.info_font,
            self.info_bg,
            self.info_text,
            self.info_show_a,
            self.info_show_b,
        )
        for widget in widgets:
            widget.blockSignals(True)
        self.info_visible.setChecked(box.visible)
        self.info_x.setValue(int(box.x))
        self.info_y.setValue(int(box.y))
        self.info_font.setValue(int(box.font_px))
        self.info_bg.setValue(int(box.bg_opacity))
        self.info_text.setValue(int(box.text_opacity))
        self.info_show_a.setChecked(box.show_a)
        self.info_show_b.setChecked(box.show_b)
        for widget in widgets:
            widget.blockSignals(False)

    def info_spec(self) -> InfoBoxSpec:
        return InfoBoxSpec(
            visible=self.info_visible.isChecked(),
            x=int(self.info_x.value()),
            y=int(self.info_y.value()),
            font_px=int(self.info_font.value()),
            bg_opacity=int(self.info_bg.value()),
            text_opacity=int(self.info_text.value()),
            show_a=self.info_show_a.isChecked(),
            show_b=self.info_show_b.isChecked(),
        )
