from throwing_scale.win_input import HOTKEY_SNAP, HOTKEY_PLANS, VK_F5, VK_F6, resolve_hotkey_vk


def test_f6_taken_falls_back_none_if_only_one_candidate():
    vk = resolve_hotkey_vk((VK_F6,), taken={VK_F6})
    assert vk is None


def test_all_taken_returns_none():
    vk = resolve_hotkey_vk((VK_F5, VK_F6), taken={VK_F5, VK_F6})
    assert vk is None


def test_default_plans_are_f5_zero_and_f6_snap():
    zero = next(plan for plan in HOTKEY_PLANS if plan.action == "平视0°")
    snap = next(plan for plan in HOTKEY_PLANS if plan.hotkey_id == HOTKEY_SNAP)
    assert zero.vks[0] == VK_F5
    assert snap.vks[0] == VK_F6
