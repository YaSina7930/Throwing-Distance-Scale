from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from throwing_scale.overlay_window import _cjk_font, _draw_text_stroked, _with_alpha
from throwing_scale.win_input import keep_topmost

BG = QColor(6, 10, 8, 210)
EDGE = QColor(40, 70, 45, 220)
NEEDLE = QColor(93, 255, 106)
DISTANCE = QColor(255, 210, 70)
TIME = QColor(120, 210, 255)
TIME_OVER = QColor(255, 150, 90)


class InfoHud(QWidget):
    def __init__(self) -> None:
        super().__init__(None)
        self.pitch = 0.0
        self.lines: list[tuple[str, QColor]] = []
        self.font_px = 22
        self.bg_opacity = 82
        self.text_opacity = 100
        self._key = None
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

    def set_lines(
        self,
        lines: list[tuple[str, QColor]],
        font_px: int,
        bg_opacity: int = 82,
        text_opacity: int = 100,
        pitch: float = 0.0,
    ) -> None:
        font_px = max(10, int(font_px))
        key = (round(pitch, 2), tuple((t, c.rgba()) for t, c in lines), font_px, bg_opacity, text_opacity)
        if key == self._key:
            return
        self._key = key
        self.pitch = float(pitch)
        self.lines = lines
        self.font_px = font_px
        self.bg_opacity = max(0, min(100, int(bg_opacity)))
        self.text_opacity = max(0, min(100, int(text_opacity)))
        line_h = self.font_px + 12
        pitch_h = int(self.font_px * 1.9)
        col_w = max(160, int(self.font_px * 9))
        width = max(240, 16 + col_w * max(len(self.lines), 1))
        height = 16 + pitch_h + line_h
        if self.width() != width or self.height() != height:
            self.setFixedSize(width, height)
        self.update()

    def place(self, x: int, y: int) -> None:
        self.move(max(0, int(x)), max(0, int(y)))

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        ta = self.text_opacity
        painter.setPen(QPen(_with_alpha(EDGE, ta), 1))
        painter.setBrush(_with_alpha(QColor(6, 10, 8), self.bg_opacity))
        painter.drawRoundedRect(1, 1, self.width() - 2, self.height() - 2, 8, 8)
        font = QFont("Consolas", self.font_px)
        font.setBold(True)
        painter.setFont(font)
        dim = _with_alpha(QColor(140, 150, 140), ta)
        plus_c = _with_alpha(NEEDLE, ta) if self.pitch > 0.0 else dim
        minus_c = _with_alpha(NEEDLE, ta) if self.pitch < 0.0 else dim
        stroke = _with_alpha(QColor(0, 0, 0), ta)
        pitch_h = int(self.font_px * 1.9)
        sign_w = self.font_px
        num_w = int(self.font_px * 3.4)
        block_w = sign_w + num_w
        sign_x = (self.width() - block_w) / 2.0
        plus_rect = QRectF(sign_x, 4, sign_w, pitch_h * 0.5)
        minus_rect = QRectF(sign_x, 4 + pitch_h * 0.38, sign_w, pitch_h * 0.5)
        _draw_text_stroked(
            painter,
            plus_rect,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            "+",
            plus_c,
            stroke,
        )
        _draw_text_stroked(
            painter,
            minus_rect,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            "-",
            minus_c,
            stroke,
        )
        _draw_text_stroked(
            painter,
            QRectF(sign_x + sign_w, 4, num_w, pitch_h),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            f"{abs(self.pitch):.1f}",
            _with_alpha(NEEDLE, ta),
            stroke,
        )
        line_h = self.font_px + 12
        y = 8 + pitch_h
        n = max(len(self.lines), 1)
        col_w = (self.width() - 16) / n
        x = 8.0
        for text, color in self.lines:
            if any("\u4e00" <= ch <= "\u9fff" for ch in text):
                painter.setFont(_cjk_font(max(10, self.font_px - 2), bold=True))
            else:
                painter.setFont(font)
            _draw_text_stroked(
                painter,
                QRectF(x, y, col_w, line_h),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                text,
                _with_alpha(color, ta),
                stroke,
            )
            x += col_w
