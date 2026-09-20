from throwing_scale.overlay_window import OverlayWindow
from throwing_scale.presets import DistancePoint


def test_overlay_paints_needle(tmp_path):
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    window = OverlayWindow()
    window.setFixedSize(220, 800)
    window.set_state(
        23.2,
        "露娜手雷",
        [DistancePoint(pitch=56.8, distance_m=62.0)],
    )
    window.show()
    app.processEvents()
    pixmap = window.grab()
    out = tmp_path / "overlay.png"
    assert pixmap.save(str(out))
    assert pixmap.width() == 220
    assert pixmap.height() == 800
    app.processEvents()
    window.hide()
