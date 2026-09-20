from dataclasses import dataclass

from throwing_scale.limits import PITCH_MAX, PITCH_MIN

@dataclass(frozen=True)
class ScaleChrome:
    bar_x: float
    bar_w: float
    tick_inner: float
    tick_outer: float
    deg_x: float
    deg_w: float
    dist_x: float
    dist_w: float
    needle_x0: float
    needle_x1: float
    needle_dot_x: float
    p_x: float
    p_w: float
    labels_left: bool


def scale_chrome(width: float, mirror: bool, pad: float = 16.0, bar_w: float = 26.0) -> ScaleChrome:
    if not mirror:
        bar_x = pad
        return ScaleChrome(
            bar_x=bar_x,
            bar_w=bar_w,
            tick_inner=bar_x + bar_w - 16,
            tick_outer=bar_x + bar_w,
            deg_x=bar_x + bar_w + 6,
            deg_w=40,
            dist_x=bar_x + bar_w + 42,
            dist_w=72,
            needle_x0=bar_x - 8,
            needle_x1=bar_x + bar_w + 10,
            needle_dot_x=bar_x - 4,
            p_x=bar_x + bar_w + 42,
            p_w=140,
            labels_left=False,
        )
    bar_x = width - pad - bar_w
    return ScaleChrome(
        bar_x=bar_x,
        bar_w=bar_w,
        tick_inner=bar_x + 16,
        tick_outer=bar_x,
        deg_x=bar_x - 46,
        deg_w=40,
        dist_x=bar_x - 118,
        dist_w=72,
        needle_x0=bar_x - 10,
        needle_x1=bar_x + bar_w + 8,
        needle_dot_x=bar_x + bar_w + 4,
        p_x=bar_x - 162,
        p_w=140,
        labels_left=True,
    )


def pitch_to_y(pitch: float, height: float, pad: float) -> float:
    center = height / 2.0
    if pitch >= 0.0:
        span = center - pad
        return center - (pitch / PITCH_MAX) * span
    span = height - pad - center
    return center + (pitch / PITCH_MIN) * span


def y_to_pitch(y: float, height: float, pad: float) -> float:
    center = height / 2.0
    if y <= center:
        span = center - pad
        if span <= 0:
            return 0.0
        return PITCH_MAX * (center - y) / span
    span = height - pad - center
    if span <= 0:
        return 0.0
    return PITCH_MIN * (y - center) / span
