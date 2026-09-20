from __future__ import annotations

import ctypes
from ctypes import wintypes
from collections.abc import Callable
from dataclasses import dataclass

user32 = ctypes.WinDLL("user32", use_last_error=True)

WM_INPUT = 0x00FF
WM_HOTKEY = 0x0312
RIDEV_INPUTSINK = 0x00000100
RID_INPUT = 0x10000003
RIM_TYPEMOUSE = 0
HID_USAGE_PAGE_GENERIC = 0x01
HID_USAGE_GENERIC_MOUSE = 0x02
MOD_NOREPEAT = 0x4000

HOTKEY_ZERO = 1
HOTKEY_SNAP = 2
HOTKEY_SNAP90 = 2
VK_F1 = 0x70
VK_F4 = 0x73
VK_F5 = 0x74
VK_F6 = 0x75
VK_F7 = 0x76
VK_F8 = 0x77
VK_F9 = 0x78
VK_F10 = 0x79
VK_F12 = 0x7B

FUNCTION_KEYS: list[tuple[str, int]] = [(f"F{i}", 0x70 + i - 1) for i in range(1, 13)]
VK_NAMES = {vk: name for name, vk in FUNCTION_KEYS}


@dataclass(frozen=True)
class HotkeyPlan:
    hotkey_id: int
    vks: tuple[int, ...]
    action: str


HOTKEY_PLANS: tuple[HotkeyPlan, ...] = (
    HotkeyPlan(HOTKEY_ZERO, (VK_F5,), "平视0°"),
    HotkeyPlan(HOTKEY_SNAP, (VK_F6,), "抬头80°"),
)


def resolve_hotkey_vk(candidates: tuple[int, ...], taken: set[int]) -> int | None:
    for vk in candidates:
        if vk not in taken:
            return vk
    return None

HWND_TOPMOST = -1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010


class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [
        ("usUsagePage", wintypes.USHORT),
        ("usUsage", wintypes.USHORT),
        ("dwFlags", wintypes.DWORD),
        ("hwndTarget", wintypes.HWND),
    ]


class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [
        ("dwType", wintypes.DWORD),
        ("dwSize", wintypes.DWORD),
        ("hDevice", wintypes.HANDLE),
        ("wParam", wintypes.WPARAM),
    ]


class RAWMOUSE(ctypes.Structure):
    _fields_ = [
        ("usFlags", wintypes.USHORT),
        ("ulButtons", wintypes.UINT),
        ("ulRawButtons", wintypes.UINT),
        ("lLastX", wintypes.LONG),
        ("lLastY", wintypes.LONG),
        ("ulExtraInformation", wintypes.UINT),
    ]


class RAWINPUT(ctypes.Structure):
    _fields_ = [
        ("header", RAWINPUTHEADER),
        ("mouse", RAWMOUSE),
    ]


user32.RegisterRawInputDevices.argtypes = [
    ctypes.POINTER(RAWINPUTDEVICE),
    wintypes.UINT,
    wintypes.UINT,
]
user32.RegisterRawInputDevices.restype = wintypes.BOOL
user32.GetRawInputData.argtypes = [
    wintypes.HANDLE,
    wintypes.UINT,
    ctypes.c_void_p,
    ctypes.POINTER(wintypes.UINT),
    wintypes.UINT,
]
user32.GetRawInputData.restype = wintypes.UINT
user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
user32.RegisterHotKey.restype = wintypes.BOOL
user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.UnregisterHotKey.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
]
user32.SetWindowPos.restype = wintypes.BOOL


def register_raw_mouse(hwnd: int) -> None:
    device = RAWINPUTDEVICE(
        usUsagePage=HID_USAGE_PAGE_GENERIC,
        usUsage=HID_USAGE_GENERIC_MOUSE,
        dwFlags=RIDEV_INPUTSINK,
        hwndTarget=hwnd,
    )
    if not user32.RegisterRawInputDevices(ctypes.byref(device), 1, ctypes.sizeof(RAWINPUTDEVICE)):
        raise ctypes.WinError(ctypes.get_last_error())


def _try_register(hwnd: int, hotkey_id: int, vk: int) -> bool:
    for mods in (MOD_NOREPEAT, 0):
        if user32.RegisterHotKey(hwnd, hotkey_id, mods, vk):
            return True
    return False


def register_hotkeys(
    hwnd: int,
    zero_vk: int = VK_F5,
    snap_vk: int = VK_F6,
) -> tuple[list[tuple[int, int, str]], list[str]]:
    bound: list[tuple[int, int, str]] = []
    failed: list[str] = []
    plans = (
        HotkeyPlan(HOTKEY_ZERO, (zero_vk,), "平视0°"),
        HotkeyPlan(HOTKEY_SNAP, (snap_vk,), "抬头80°"),
    )
    for plan in plans:
        chosen = None
        for vk in plan.vks:
            if _try_register(hwnd, plan.hotkey_id, vk):
                chosen = vk
                break
        if chosen is None:
            failed.append(plan.action)
        else:
            bound.append((plan.hotkey_id, chosen, f"{VK_NAMES.get(chosen, hex(chosen))} {plan.action}"))
    return bound, failed


def unregister_hotkeys(hwnd: int) -> None:
    for hotkey_id in (HOTKEY_ZERO, HOTKEY_SNAP):
        user32.UnregisterHotKey(hwnd, hotkey_id)


def keep_topmost(hwnd: int) -> None:
    user32.SetWindowPos(
        hwnd,
        HWND_TOPMOST,
        0,
        0,
        0,
        0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
    )


def read_raw_mouse_delta(lparam: int) -> tuple[int, int] | None:
    size = wintypes.UINT(0)
    header_size = ctypes.sizeof(RAWINPUTHEADER)
    user32.GetRawInputData(lparam, RID_INPUT, None, ctypes.byref(size), header_size)
    if size.value == 0:
        return None
    buf = ctypes.create_string_buffer(size.value)
    got = user32.GetRawInputData(
        lparam, RID_INPUT, buf, ctypes.byref(size), header_size
    )
    if got == 0xFFFFFFFF or got == 0:
        return None
    raw = RAWINPUT.from_buffer_copy(buf)
    if raw.header.dwType != RIM_TYPEMOUSE:
        return None
    dx, dy = raw.mouse.lLastX, raw.mouse.lLastY
    if dx == 0 and dy == 0:
        return None
    return dx, dy


class NativeFilter:
    def __init__(
        self,
        on_mouse: Callable[[int, int], None],
        on_hotkey: Callable[[int], None],
    ) -> None:
        from PySide6.QtCore import QAbstractNativeEventFilter

        class _Filter(QAbstractNativeEventFilter):
            def nativeEventFilter(inner_self, eventType, message):
                if bytes(eventType) != b"windows_generic_MSG":
                    return False
                msg = wintypes.MSG.from_address(int(message))
                if msg.message == WM_INPUT:
                    delta = read_raw_mouse_delta(int(msg.lParam))
                    if delta is not None:
                        on_mouse(delta[0], delta[1])
                elif msg.message == WM_HOTKEY:
                    on_hotkey(int(msg.wParam))
                return False

        self._filter = _Filter()

    def qt_filter(self):
        return self._filter
