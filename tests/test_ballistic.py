import math

from throwing_scale.ballistic import (
    FUSE_S,
    THROW_DELAY_S,
    Fit,
    distance_at,
    fit_throw,
    flight_time,
    impact_at,
    is_timed_instant,
    timed_instant_grade,
    throw_range,
    tick_distances,
)
from throwing_scale.presets import C4_POINTS, LEFT_LOW_POINTS, LONG_THROW_POINTS, ULT_POINTS, WOLF_CANNON_POINTS


def test_flat_45_degrees_is_v_squared_over_g():
    v = 30.0
    g = 9.81
    r = throw_range(45.0, v=v, height=0.0, g=g)
    assert abs(r - (v * v / g)) < 1e-6


def test_fit_corrects_long_throw_points_within_three_meters():
    fit = fit_throw(LONG_THROW_POINTS)
    assert isinstance(fit, Fit)
    for point in LONG_THROW_POINTS:
        pred = distance_at(point.pitch, fit)
        assert pred is not None
        assert abs(pred - point.distance_m) < 3.0


def test_distance_increases_from_10_to_30_degrees():
    fit = fit_throw(LONG_THROW_POINTS)
    r10 = distance_at(10.0, fit)
    r30 = distance_at(30.0, fit)
    assert r10 is not None and r30 is not None
    assert r30 > r10


def test_zero_degree_has_a_range():
    fit = fit_throw(LONG_THROW_POINTS)
    pred = distance_at(0.0, fit)
    assert pred is not None
    assert 15.0 < pred < 30.0


def test_flat_flight_time_at_45():
    v = 30.0
    g = 9.81
    t = flight_time(45.0, v=v, height=0.0, g=g)
    assert abs(t - (2 * v * math.sin(math.radians(45.0)) / g)) < 1e-6


def test_displayed_seconds_are_flight_plus_throw_delay():
    fit = fit_throw(LONG_THROW_POINTS)
    hit = impact_at(25.0, fit)
    assert hit is not None
    true = 25.0 + fit.bias
    boom = flight_time(true, fit.v, fit.height) + THROW_DELAY_S + fit.time_offset
    assert abs(hit[1] - boom) < 1e-9


def test_nineteen_degrees_remaining_plus_throw_is_2_8s():
    fit = fit_throw(LONG_THROW_POINTS)
    hit = impact_at(19.0, fit)
    assert hit is not None
    assert abs(hit[0] - 60.0) < 3.0
    assert abs(hit[1] - 2.8) < 0.08


def test_left_low_fit_hits_measured_points():
    fit = fit_throw(LEFT_LOW_POINTS)
    assert fit is not None
    for point in LEFT_LOW_POINTS:
        pred = distance_at(point.pitch, fit)
        assert pred is not None
        assert abs(pred - point.distance_m) < 3.0


def test_c4_fit_hits_measured_points():
    fit = fit_throw(C4_POINTS)
    assert fit is not None
    for point in C4_POINTS:
        true = point.pitch + fit.bias
        pred = throw_range(true, fit.v, fit.height)
        limit = 5.0 if point.pitch >= 70 else 3.0
        assert abs(pred - point.distance_m) < limit


def test_timed_instant_grades():
    assert timed_instant_grade(1.99, 3.0) is None
    assert timed_instant_grade(2.0, 3.0) == "early"
    assert timed_instant_grade(2.49, 3.0) == "early"
    assert timed_instant_grade(2.5, 3.0) == "late"
    assert timed_instant_grade(3.0, 3.0) == "late"
    assert timed_instant_grade(3.04, 3.0) == "late"
    assert timed_instant_grade(3.09, 3.0) is None
    assert is_timed_instant(2.2, 3.0) is True
    assert is_timed_instant(1.9, 3.0) is False


def test_ult_70m_is_instant_boundary():
    fit = fit_throw(ULT_POINTS, delay=0.0, range_time_anchors=((70.0, 3.0),))
    assert fit is not None
    best = None
    deg = 0.0
    while deg <= 45.0001:
        hit = impact_at(deg, fit, delay=0.0, use_offset=True)
        if hit is not None:
            err = abs(hit[0] - 70.0)
            if best is None or err < best[0]:
                best = (err, deg, hit[0], hit[1])
        deg += 0.5
    assert best is not None
    assert best[0] < 12.0
    assert best[1] <= 45.0
    assert abs(best[3] - 3.0) < 0.2
    assert timed_instant_grade(best[3], 3.0) == "late"
    for point in ULT_POINTS:
        pred = distance_at(point.pitch, fit)
        assert pred is not None
        assert abs(pred - point.distance_m) < 4.0
    ticks = tick_distances(
        fit,
        delay=0.0,
        use_offset=True,
        fuse_s=3.0,
        max_boom=4.0,
        instant_max_range=70.0,
        instant_max_pitch=45.0,
        step=5.0,
    )
    assert all(boom <= 4.0 + 1e-9 for _p, _r, boom, _g in ticks)
    assert all(g is None or r <= 70.6 for _p, r, _b, g in ticks)
    late = [(p, r) for p, r, _b, g in ticks if g == "late"]
    assert late
    assert min(abs(r - 70.0) for _p, r in late) < 2.0
    assert 15.0 in [p for p, _r, _b, _g in ticks]


def test_wolf_cannon_82m_is_instant_boundary():
    fit = fit_throw(WOLF_CANNON_POINTS, delay=0.0, range_time_anchors=((82.0, 3.0),))
    assert fit is not None
    best = None
    deg = 0.0
    while deg <= 45.0001:
        hit = impact_at(deg, fit, delay=0.0, use_offset=True)
        if hit is not None:
            err = abs(hit[0] - 82.0)
            if best is None or err < best[0]:
                best = (err, deg, hit[0], hit[1])
        deg += 0.5
    assert best is not None
    assert best[0] < 15.0
    assert timed_instant_grade(best[3], 3.0) == "late"
    ticks = tick_distances(
        fit,
        delay=0.0,
        use_offset=True,
        fuse_s=3.0,
        max_boom=4.0,
        instant_max_range=82.0,
        instant_max_pitch=45.0,
        step=5.0,
    )
    assert all(g is None or r <= 82.6 for _p, r, _b, g in ticks)
    late = [(p, r) for p, r, _b, g in ticks if g == "late"]
    assert late
    assert min(abs(r - 82.0) for _p, r in late) < 2.5
    meters = [round(r) for _p, r, _b, _g in ticks]
    assert len(meters) == len(set(meters))
    for point in WOLF_CANNON_POINTS:
        true = point.pitch + fit.bias
        pred = throw_range(true, fit.v, fit.height)
        assert abs(pred - point.distance_m) < 8.0


def test_over_fuse_hang_is_still_marked():
    fit = fit_throw(LONG_THROW_POINTS)
    hit = impact_at(70.0, fit)
    assert hit is not None
    assert hit[1] > FUSE_S
