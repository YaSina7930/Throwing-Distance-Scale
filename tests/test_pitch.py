from throwing_scale.pitch import PitchTracker


def test_starts_at_zero():
    tracker = PitchTracker()
    assert tracker.pitch == 0.0


def test_mouse_up_increases_pitch():
    tracker = PitchTracker(counts_per_degree=10.0)
    tracker.add_raw_delta(dx=0, dy=-20)
    assert tracker.pitch == 2.0


def test_mouse_down_decreases_pitch():
    tracker = PitchTracker(counts_per_degree=10.0)
    tracker.add_raw_delta(dx=0, dy=30)
    assert tracker.pitch == -3.0


def test_pitch_clamped_to_stand_limits():
    tracker = PitchTracker(counts_per_degree=1.0)
    tracker.add_raw_delta(dx=0, dy=-200)
    assert tracker.pitch == 80.0
    tracker.add_raw_delta(dx=0, dy=500)
    assert tracker.pitch == -75.0


def test_calibrate_zero_resets_pitch_keeps_sensitivity():
    tracker = PitchTracker(counts_per_degree=10.0)
    tracker.add_raw_delta(dx=0, dy=-50)
    tracker.calibrate_zero()
    assert tracker.pitch == 0.0
    assert tracker.counts_per_degree == 10.0
    tracker.add_raw_delta(dx=0, dy=-10)
    assert tracker.pitch == 1.0


def test_calibrate_known_angle_sets_sensitivity_from_counts_since_zero():
    tracker = PitchTracker(counts_per_degree=1.0)
    tracker.calibrate_zero()
    tracker.add_raw_delta(dx=0, dy=-475)
    tracker.calibrate_known_angle(47.5)
    assert tracker.counts_per_degree == 10.0
    assert tracker.pitch == 47.5


def test_calibrate_known_angle_rejects_zero_angle():
    tracker = PitchTracker()
    tracker.add_raw_delta(dx=0, dy=-10)
    try:
        tracker.calibrate_known_angle(0.0)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_invert_y_flips_mouse_direction():
    tracker = PitchTracker(counts_per_degree=10.0, invert_y=True)
    tracker.add_raw_delta(dx=0, dy=-20)
    assert tracker.pitch == -2.0


def test_hit_top_then_mouse_down_moves_immediately():
    tracker = PitchTracker(counts_per_degree=1.0)
    tracker.add_raw_delta(dx=0, dy=-400)
    assert tracker.pitch == 80.0
    tracker.add_raw_delta(dx=0, dy=10)
    assert tracker.pitch == 70.0


def test_hit_bottom_then_mouse_up_moves_immediately():
    tracker = PitchTracker(counts_per_degree=1.0)
    tracker.add_raw_delta(dx=0, dy=400)
    assert tracker.pitch == -75.0
    tracker.add_raw_delta(dx=0, dy=-10)
    assert tracker.pitch == -65.0


def test_calibrate_still_uses_unclamped_mouse_travel():
    tracker = PitchTracker(counts_per_degree=1.0)
    tracker.calibrate_zero()
    tracker.add_raw_delta(dx=0, dy=-475)
    tracker.calibrate_known_angle(47.5)
    assert tracker.counts_per_degree == 10.0
    assert tracker.pitch == 47.5


def test_snap_to_prone_look_up_80():
    tracker = PitchTracker(counts_per_degree=40.0)
    tracker.add_raw_delta(dx=0, dy=-80)
    tracker.snap_to(80.0)
    assert tracker.pitch == 80.0
    assert tracker.counts_per_degree == 40.0
    tracker.add_raw_delta(dx=0, dy=40)
    assert tracker.pitch == 79.0


def test_snap_to_zero_is_same_as_calibrate_zero():
    tracker = PitchTracker(counts_per_degree=20.0)
    tracker.add_raw_delta(dx=0, dy=-100)
    tracker.snap_to(0.0)
    assert tracker.pitch == 0.0
    tracker.add_raw_delta(dx=0, dy=-20)
    assert tracker.pitch == 1.0


def test_set_counts_per_degree_keeps_current_pitch():
    tracker = PitchTracker(counts_per_degree=10.0)
    tracker.add_raw_delta(dx=0, dy=-50)
    assert tracker.pitch == 5.0
    tracker.set_counts_per_degree(20.0)
    assert tracker.pitch == 5.0
    tracker.add_raw_delta(dx=0, dy=-20)
    assert tracker.pitch == 6.0
