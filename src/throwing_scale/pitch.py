from __future__ import annotations

from throwing_scale.limits import PITCH_MAX, PITCH_MIN


class PitchTracker:
    def __init__(self, counts_per_degree: float = 80.0, invert_y: bool = False) -> None:
        if counts_per_degree <= 0:
            raise ValueError("counts_per_degree must be positive")
        self.counts_per_degree = float(counts_per_degree)
        self.invert_y = invert_y
        self.pitch = 0.0
        self._counts_since_zero = 0.0
        self._calib_counts = 0.0

    def _limits(self) -> tuple[float, float]:
        return PITCH_MIN * self.counts_per_degree, PITCH_MAX * self.counts_per_degree

    def add_raw_delta(self, dx: float, dy: float) -> float:
        signed = -dy if not self.invert_y else dy
        self._calib_counts += signed
        lo, hi = self._limits()
        self._counts_since_zero = max(lo, min(hi, self._counts_since_zero + signed))
        self.pitch = self._counts_since_zero / self.counts_per_degree
        return self.pitch

    def set_counts_per_degree(self, value: float) -> None:
        if value <= 0:
            raise ValueError("counts_per_degree must be positive")
        self.counts_per_degree = float(value)
        self._counts_since_zero = self.pitch * self.counts_per_degree
        self._calib_counts = self._counts_since_zero

    def snap_to(self, angle: float) -> None:
        self.pitch = max(PITCH_MIN, min(PITCH_MAX, float(angle)))
        self._counts_since_zero = self.pitch * self.counts_per_degree
        self._calib_counts = self._counts_since_zero

    def calibrate_zero(self) -> None:
        self.snap_to(0.0)

    def calibrate_known_angle(self, angle: float) -> None:
        if angle == 0.0:
            raise ValueError("known angle must be non-zero")
        if self._calib_counts == 0.0:
            raise ValueError("no mouse movement since zero")
        self.counts_per_degree = abs(self._calib_counts / angle)
        direction = 1.0 if self._calib_counts >= 0 else -1.0
        self.pitch = max(PITCH_MIN, min(PITCH_MAX, abs(angle) * direction))
        self._counts_since_zero = self.pitch * self.counts_per_degree
        self._calib_counts = self._counts_since_zero
