from throwing_scale.scale_geom import pitch_to_y, scale_chrome, y_to_pitch


def test_plus_80_maps_to_top_pad():
    assert pitch_to_y(80.0, height=200, pad=20) == 20.0


def test_minus_75_maps_to_bottom_pad():
    assert pitch_to_y(-75.0, height=200, pad=20) == 180.0


def test_zero_is_visual_center_not_range_average():
    assert pitch_to_y(0.0, height=200, pad=20) == 100.0


def test_mirror_puts_labels_on_the_opposite_side_of_the_bar():
    left = scale_chrome(220, False)
    right = scale_chrome(220, True)
    assert left.bar_x < left.deg_x
    assert right.deg_x + right.deg_w <= right.bar_x + 1e-6
    assert right.bar_x > left.bar_x


def test_y_to_pitch_roundtrip():
    for pitch in (-75.0, -45.0, 0.0, 23.2, 56.77, 80.0):
        y = pitch_to_y(pitch, height=800, pad=40)
        assert abs(y_to_pitch(y, height=800, pad=40) - pitch) < 1e-9
