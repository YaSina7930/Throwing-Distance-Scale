from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPainter, QPen
from PySide6.QtWidgets import QWidget

from throwing_scale.ballistic import FUSE_S, NEAR_S
from throwing_scale.limits import PITCH_MAX, PITCH_MIN
from throwing_scale.presets import DistancePoint
from throwing_scale.scale_geom import pitch_to_y, scale_chrome
from throwing_scale.win_input import keep_topmost

NEEDLE = QColor(93, 255, 106)
NEEDLE_DIM = QColor(93, 255, 106, 80)
TICK = QColor(210, 220, 210)
TICK_MINOR = QColor(120, 140, 120)
ZERO = QColor(255, 255, 255)
DISTANCE = QColor(255, 210, 70)
BG = QColor(6, 10, 8, 210)
BAR_EDGE = QColor(40, 70, 45, 220)
STROKE = QColor(0, 0, 0)


def _cjk_font(size: int, bold: bool = False) -> QFont:
    families = set(QFontDatabase.families())
    for name in ("Microsoft YaHei", "微软雅黑", "SimHei", "NSimSun", "Segoe UI"):
        if name in families:
            font = QFont(name, size)
            font.setBold(bold)
            return font
    font = QFont()
    font.setPointSize(size)
    font.setBold(bold)
    return font


def _with_alpha(color: QColor, pct: int) -> QColor:
    out = QColor(color)
    out.setAlpha(max(0, min(255, int(round(255 * pct / 100.0)))))
    return out


def instant_color(grade: str) -> QColor:
    if grade == "late":
        return QColor(255, 36, 36)
    return QColor(80, 220, 255)


def _time_color(seconds: float) -> QColor:
    if seconds > FUSE_S:
        return QColor(255, 150, 90)
    if seconds <= NEAR_S:
        return QColor(255, 90, 180)
    return QColor(120, 210, 255)


def _draw_text_stroked(
    painter: QPainter,
    rect: QRectF,
    flags: Qt.AlignmentFlag,
    text: str,
    fill: QColor,
    stroke: QColor | None = None,
) -> None:
    painter.save()
    edge = stroke if stroke is not None else STROKE
    for dx in (-2, -1, 0, 1, 2):
        for dy in (-2, -1, 0, 1, 2):
            if dx == 0 and dy == 0:
                continue
            painter.setPen(edge)
            painter.drawText(rect.translated(dx, dy), flags, text)
    painter.setPen(fill)
    painter.drawText(rect, flags, text)
    painter.restore()


class OverlayWindow(QWidget):
    def __init__(self) -> None:
        super().__init__(None)
        self.pitch = 0.0
        self.preset_name = ""
        self.points: list[DistancePoint] = []
        self.tick_labels: list[tuple[float, float, float, str | None]] = []
        self.current_distance: float | None = None
        self.current_cook: float | None = None
        self.current_grade: str | None = None
        self.show_scale = True
        self.show_preset = True
        self.mirror = False
        self.font_px = 13
        self.show_time = True
        self.show_instant = False
        self.bg_opacity = 82
        self.text_opacity = 100
        self._pad = 36
        self._state_key = None
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFixedWidth(220)
        self._topmost = QTimer(self)
        self._topmost.setInterval(400)
        self._topmost.timeout.connect(self._bump_topmost)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._topmost.start()
        self._bump_topmost()

    def hideEvent(self, event) -> None:
        self._topmost.stop()
        super().hideEvent(event)

    def _bump_topmost(self) -> None:
        hwnd = int(self.winId())
        if hwnd:
            keep_topmost(hwnd)

    def set_state(
        self,
        pitch: float,
        preset_name: str,
        points: list[DistancePoint],
        tick_labels: list[tuple[float, float, float, str | None]] | None = None,
        current_distance: float | None = None,
        current_cook: float | None = None,
        current_grade: str | None = None,
        show_scale: bool = True,
        show_preset: bool = True,
        mirror: bool = False,
        font_px: int = 13,
        bg_opacity: int = 82,
        text_opacity: int = 100,
        show_time: bool = True,
        show_instant: bool = False,
    ) -> None:
        font_px = max(8, int(font_px))
        key = (
            round(pitch, 2),
            preset_name,
            current_distance,
            current_cook,
            show_scale,
            show_preset,
            mirror,
            font_px,
            bg_opacity,
            text_opacity,
            show_time,
            show_instant,
            current_grade,
            len(tick_labels or ()),
        )
        if key == self._state_key:
            return
        self._state_key = key
        self.pitch = pitch
        self.preset_name = preset_name
        self.points = points
        self.tick_labels = tick_labels or []
        self.current_distance = current_distance
        self.current_cook = current_cook
        self.current_grade = current_grade
        self.show_scale = show_scale
        self.show_preset = show_preset
        self.mirror = mirror
        self.bg_opacity = max(0, min(100, int(bg_opacity)))
        self.text_opacity = max(0, min(100, int(text_opacity)))
        self.show_time = bool(show_time)
        self.show_instant = bool(show_instant)
        self.current_grade = current_grade
        if self.font_px != font_px:
            self.font_px = font_px
            self.setFixedWidth(max(220, self.font_px * 16))
        self.update()

    def place(self, screen_geo, x: int, height_pct: int = 78) -> None:
        pct = max(10, min(100, int(height_pct)))
        height = int(screen_geo.height() * (pct / 100.0))
        y = screen_geo.y() + (screen_geo.height() - height) // 2
        self.setFixedHeight(height)
        self.move(screen_geo.x() + x, y)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        h = self.height()
        pad = self._pad
        chrome = scale_chrome(self.width(), self.mirror)
        bar_x, bar_w = chrome.bar_x, chrome.bar_w
        text_align = (
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            if chrome.labels_left
            else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        name_align = (
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            if self.mirror
            else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )

        ta = self.text_opacity
        stroke = _with_alpha(STROKE, ta)
        if self.show_scale:
            painter.setPen(QPen(_with_alpha(BAR_EDGE, ta), 1))
            painter.setBrush(_with_alpha(QColor(6, 10, 8), self.bg_opacity))
            painter.drawRoundedRect(bar_x - 6, pad - 14, bar_w + 12, h - 2 * pad + 28, 6, 6)

        start = int(PITCH_MIN)
        stop = int(PITCH_MAX)
        if not self.show_scale:
            start, stop = 0, -1
        tick_font = max(8, self.font_px - 2)
        painter.setFont(_cjk_font(tick_font))
        for deg in range(start, stop + 1, 5):
            y = pitch_to_y(float(deg), h, pad)
            major = deg % 10 == 0 or deg in (start, stop)
            tick_w = 16 if major else 8
            if chrome.labels_left:
                tick_a, tick_b = chrome.tick_outer, chrome.tick_outer + tick_w
            else:
                tick_a, tick_b = chrome.tick_outer - tick_w, chrome.tick_outer
            painter.setPen(QPen(_with_alpha(TICK if major else TICK_MINOR, ta), 1.2 if major else 1))
            painter.drawLine(QPointF(tick_a, y), QPointF(tick_b, y))
            if major:
                _draw_text_stroked(
                    painter,
                    QRectF(chrome.deg_x, y - 8, chrome.deg_w, 16),
                    text_align,
                    f"{deg}",
                    _with_alpha(TICK, ta),
                    stroke,
                )

        if self.show_scale:
            y0 = pitch_to_y(0.0, h, pad)
            painter.setPen(QPen(_with_alpha(ZERO, ta), 1.6))
            painter.drawLine(QPointF(bar_x - 4, y0), QPointF(bar_x + bar_w + 4, y0))

        if self.show_scale:
            for pitch, rng, cook, grade in self.tick_labels:
                y = pitch_to_y(pitch, h, pad)
                if self.show_time:
                    _draw_text_stroked(
                        painter,
                        QRectF(chrome.dist_x, y - 12, chrome.dist_w, 14),
                        text_align,
                        f"{rng:.0f}m",
                        _with_alpha(DISTANCE, ta),
                        stroke,
                    )
                    _draw_text_stroked(
                        painter,
                        QRectF(chrome.dist_x, y + 1, chrome.dist_w, 14),
                        text_align,
                        f"{cook:.1f}s",
                        _with_alpha(_time_color(cook), ta),
                        stroke,
                    )
                elif self.show_instant and grade:
                    _draw_text_stroked(
                        painter,
                        QRectF(chrome.dist_x, y - 12, chrome.dist_w, 14),
                        text_align,
                        f"{rng:.0f}m",
                        _with_alpha(DISTANCE, ta),
                        stroke,
                    )
                    _draw_text_stroked(
                        painter,
                        QRectF(chrome.dist_x, y + 1, chrome.dist_w, 14),
                        text_align,
                        "瞬",
                        _with_alpha(instant_color(grade), ta),
                        stroke,
                    )
                else:
                    _draw_text_stroked(
                        painter,
                        QRectF(chrome.dist_x, y - 8, chrome.dist_w, 16),
                        text_align,
                        f"{rng:.0f}m",
                        _with_alpha(DISTANCE, ta),
                        stroke,
                    )

        if not self.show_scale:
            if self.show_preset and self.preset_name:
                painter.setFont(_cjk_font(self.font_px))
                _draw_text_stroked(
                    painter,
                    QRectF(4, 4, self.width() - 8, 20),
                    name_align,
                    self.preset_name,
                    _with_alpha(QColor(220, 230, 220), ta),
                    stroke,
                )
            return

        y = pitch_to_y(self.pitch, h, pad)
        painter.setPen(QPen(_with_alpha(NEEDLE_DIM, ta), 6))
        painter.drawLine(QPointF(chrome.needle_x0, y), QPointF(chrome.needle_x1, y))
        painter.setPen(QPen(_with_alpha(NEEDLE, ta), 2.4))
        painter.drawLine(QPointF(chrome.needle_x0, y), QPointF(chrome.needle_x1, y))
        painter.setBrush(_with_alpha(NEEDLE, ta))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(chrome.needle_dot_x, y), 3.2, 3.2)

        label_font = QFont("Consolas", self.font_px)
        label_font.setBold(True)
        painter.setFont(label_font)
        _draw_text_stroked(
            painter,
            QRectF(chrome.p_x, y - 22, chrome.p_w, 20),
            text_align,
            f"P:{self.pitch:+.1f}°"
            + (
                f"  {self.current_distance:.0f}m {self.current_cook:.1f}s"
                if self.show_time and self.current_distance is not None and self.current_cook is not None
                else (
                    f"  {self.current_distance:.0f}m 瞬"
                    if self.show_instant and self.current_grade and self.current_distance is not None
                    else (f"  {self.current_distance:.0f}m" if self.current_distance is not None else "")
                )
            ),
            _with_alpha(NEEDLE, ta),
            stroke,
        )

        if self.show_preset and self.preset_name:
            painter.setFont(_cjk_font(self.font_px))
            _draw_text_stroked(
                painter,
                QRectF(4, 4, self.width() - 8, self.font_px + 8),
                name_align,
                self.preset_name,
                _with_alpha(QColor(220, 230, 220), ta),
                stroke,
            )
