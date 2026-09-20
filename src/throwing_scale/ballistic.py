from __future__ import annotations

import math
from dataclasses import dataclass

from throwing_scale.presets import DistancePoint

G = 9.81
FUSE_S = 5.0
THROW_DELAY_S = 0.2
NEAR_S = 3.0
INSTANT_EARLY_S = 2.0
INSTANT_LATE_S = 2.5
INSTANT_TOLERANCE_S = 0.5
MAX_DISPLAY_S = 4.0
ULT_INSTANT_RANGE_M = 70.0


TIME_ANCHORS = ((19.0, 2.8),)


@dataclass(frozen=True)
class Fit:
    v: float
    height: float
    bias: float
    time_offset: float = 0.0


def flight_time(pitch_deg: float, v: float, height: float, g: float = G) -> float:
    if v <= 0:
        return 0.0
    theta = math.radians(pitch_deg)
    vy = v * math.sin(theta)
    disc = vy * vy + 2.0 * g * max(0.0, height)
    if disc < 0:
        return 0.0
    return (vy + math.sqrt(disc)) / g


def throw_range(pitch_deg: float, v: float, height: float, g: float = G) -> float:
    theta = math.radians(pitch_deg)
    vx = v * math.cos(theta)
    if vx <= 0:
        return 0.0
    return vx * flight_time(pitch_deg, v, height, g)


def impact_at(
    pitch_deg: float,
    fit: Fit,
    delay: float = THROW_DELAY_S,
    use_offset: bool = True,
) -> tuple[float, float] | None:
    true_pitch = pitch_deg + fit.bias
    if true_pitch < 0.0 or true_pitch > 90.0:
        return None
    rng = throw_range(true_pitch, fit.v, fit.height)
    if rng < 0.3:
        return None
    boom = flight_time(true_pitch, fit.v, fit.height) + delay
    if use_offset:
        boom += fit.time_offset
    return rng, boom


def timed_instant_grade(boom: float, fuse_s: float) -> str | None:
    if boom < INSTANT_EARLY_S:
        return None
    if boom < INSTANT_LATE_S:
        return "early"
    if boom <= fuse_s + 0.08:
        return "late"
    return None


def is_timed_instant(boom: float, fuse_s: float, tol: float = INSTANT_TOLERANCE_S) -> bool:
    return timed_instant_grade(boom, fuse_s) is not None


def distance_at(pitch_deg: float, fit: Fit) -> float | None:
    hit = impact_at(pitch_deg, fit)
    return None if hit is None else hit[0]


def fit_throw(
    points: list[DistancePoint],
    delay: float = THROW_DELAY_S,
    range_time_anchors: tuple[tuple[float, float], ...] = (),
) -> Fit | None:
    usable = [p for p in points if p.distance_m > 0]
    if len(usable) < 3:
        return None
    best: tuple[float, Fit] | None = None
    v = 10.0
    while v <= 40.0001:
        h = 0.0
        while h <= 4.0001:
            bias = -5.0
            while bias <= 15.0001:
                err = 0.0
                for point in usable:
                    pred = throw_range(point.pitch + bias, v, h)
                    err += (pred - point.distance_m) ** 2
                if best is None or err < best[0]:
                    best = (err, Fit(v=v, height=h, bias=bias))
                bias += 0.25
            h += 0.1
        v += 0.25
    if best is None:
        return None
    fit = best[1]
    known = {round(p.pitch, 1) for p in usable}
    offsets = []
    for pitch, boom in TIME_ANCHORS:
        if round(pitch, 1) not in known:
            continue
        raw = flight_time(pitch + fit.bias, fit.v, fit.height) + delay
        offsets.append(boom - raw)
    for target_r, target_t in range_time_anchors:
        best: tuple[float, float, float] | None = None
        deg = 0.0
        while deg <= 45.0001:
            rng = throw_range(deg + fit.bias, fit.v, fit.height)
            err = abs(rng - target_r)
            if rng >= 0.3 and (best is None or err < best[0]):
                best = (err, deg, rng)
            deg += 0.5
        if best is not None and best[0] <= 12.0:
            raw = flight_time(best[1] + fit.bias, fit.v, fit.height) + delay
            offsets.append(target_t - raw)
    if offsets:
        fit = Fit(
            v=fit.v,
            height=fit.height,
            bias=fit.bias,
            time_offset=sum(offsets) / len(offsets),
        )
    return fit


def _grade_for(
    pitch: float,
    rng: float,
    boom: float,
    fuse_s: float | None,
    instant_max_range: float | None,
    instant_max_pitch: float | None,
) -> str | None:
    grade = timed_instant_grade(boom, fuse_s) if fuse_s is not None else None
    if grade and instant_max_range is not None and rng > instant_max_range + 0.6:
        return None
    if grade and instant_max_pitch is not None and pitch > instant_max_pitch:
        return None
    return grade


def _pitch_for_boom(
    fit: Fit,
    delay: float,
    use_offset: bool,
    target_t: float,
    max_pitch: float = 45.0,
) -> float | None:
    best: tuple[float, float] | None = None
    deg = 0.0
    while deg <= max_pitch + 1e-9:
        hit = impact_at(deg, fit, delay=delay, use_offset=use_offset)
        if hit is not None:
            err = abs(hit[1] - target_t)
            if best is None or err < best[0]:
                best = (err, deg)
        deg += 0.1
    if best is None or best[0] > 0.08:
        return None
    return best[1]


def tick_distances(
    fit: Fit,
    lo: float = 0.0,
    hi: float = 80.0,
    step: float = 5.0,
    delay: float = THROW_DELAY_S,
    use_offset: bool = True,
    fuse_s: float | None = None,
    max_boom: float | None = None,
    instant_max_range: float | None = None,
    instant_max_pitch: float | None = None,
) -> list[tuple[float, float, float, str | None]]:
    out: list[tuple[float, float, float, str | None]] = []
    pitch = lo
    while pitch <= hi + 1e-9:
        hit = impact_at(pitch, fit, delay=delay, use_offset=use_offset)
        if hit is not None:
            rng, boom = hit
            if max_boom is None or boom <= max_boom:
                grade = _grade_for(pitch, rng, boom, fuse_s, instant_max_range, instant_max_pitch)
                out.append((pitch, rng, boom, grade))
        pitch += step
    if fuse_s is not None:
        extras = [INSTANT_EARLY_S, INSTANT_LATE_S, fuse_s]
        existing = [p for p, _r, _b, _g in out]
        cap = instant_max_pitch if instant_max_pitch is not None else 45.0
        for target_t in extras:
            extra_p = _pitch_for_boom(fit, delay, use_offset, target_t, cap)
            if extra_p is None:
                continue
            if any(abs(extra_p - p) < 0.4 for p in existing):
                continue
            hit = impact_at(extra_p, fit, delay=delay, use_offset=use_offset)
            if hit is None:
                continue
            rng, boom = hit
            if max_boom is not None and boom > max_boom:
                continue
            if any(round(rng) == round(r) for _p, r, _b, _g in out):
                continue
            grade = _grade_for(extra_p, rng, boom, fuse_s, instant_max_range, instant_max_pitch)
            out.append((extra_p, rng, boom, grade))
            existing.append(extra_p)
        start_p = _pitch_for_boom(fit, delay, use_offset, INSTANT_LATE_S, cap)
        end_p = _pitch_for_boom(fit, delay, use_offset, fuse_s, cap)
        if instant_max_range is not None:
            best_r: tuple[float, float] | None = None
            deg = 0.0
            while deg <= cap + 1e-9:
                hit = impact_at(deg, fit, delay=delay, use_offset=use_offset)
                if hit is not None:
                    err = abs(hit[0] - instant_max_range)
                    if best_r is None or err < best_r[0]:
                        best_r = (err, deg)
                deg += 0.1
            if best_r is not None and best_r[0] <= 2.0:
                end_p = best_r[1] if end_p is None else min(end_p, best_r[1])
        if start_p is not None and end_p is not None and end_p >= start_p:
            deg = start_p
            while deg <= end_p + 0.05:
                if not any(abs(deg - p) < 0.35 for p in existing):
                    hit = impact_at(deg, fit, delay=delay, use_offset=use_offset)
                    if hit is not None and (max_boom is None or hit[1] <= max_boom):
                        rng, boom = hit
                        if not any(round(rng) == round(r) for _p, r, _b, _g in out):
                            grade = _grade_for(deg, rng, boom, fuse_s, instant_max_range, instant_max_pitch)
                            if grade is None and rng <= (instant_max_range or rng) + 0.6 and INSTANT_LATE_S - 0.05 <= boom <= fuse_s + 0.08:
                                grade = "late"
                            out.append((deg, rng, boom, grade))
                            existing.append(deg)
                deg += 1.0
        out.sort(key=lambda item: item[0])
    return out
