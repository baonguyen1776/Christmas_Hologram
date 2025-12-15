"""
Gesture Controller - Simple threshold-based gesture detection
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class GestureConfig:
    """Gesture thresholds"""
    pinch_open: float = 80
    pinch_close: float = 50
    pinch_zoom: float = 150
    cooldown_frames: int = 30
    smoothing_window: int = 3
    # Compatibility
    pinch_unzoom: float = 50
    arm_zone_min: float = 50
    arm_zone_max: float = 75
    confirm_frames: int = 3


class GestureController:
    def __init__(self, config: Optional[GestureConfig] = None):
        self.config = config or GestureConfig()
        self.distance_history = []
        self.angle_history = []
        self.smoothed_distance = 0
        self.smoothed_angle = 0
        self.prev_angle = 0
        self.current_time = 0
        self.last_trigger_time = -1000
        self.armed = True
        self.pending_gesture = None
        self.confirm_counter = 0

    def update(self, raw_distance: float, raw_angle: float, index_x: float) -> dict:
        self.current_time += 1
        self._update_smoothing(raw_distance, raw_angle)
        
        result = {
            'distance': self.smoothed_distance,
            'angle': self.smoothed_angle,
            'angle_delta': self._get_angle_delta(),
            'triggered': None,
            'confirming': None,
            'progress': 0,
            'can_gesture': self._can_gesture(),
            'armed': True
        }
        
        if self.smoothed_distance <= 0 or not self._can_gesture():
            return result
        
        d = self.smoothed_distance
        
        if d < self.config.pinch_close:
            result['triggered'] = 'pinch_close'
            self._on_triggered()
        elif d > self.config.pinch_zoom:
            result['triggered'] = 'pinch_zoom'
            self._on_triggered()
        elif d > self.config.pinch_open:
            result['triggered'] = 'pinch_open'
            self._on_triggered()
        
        return result

    def _update_smoothing(self, raw_distance: float, raw_angle: float):
        self.distance_history.append(raw_distance)
        if len(self.distance_history) > self.config.smoothing_window:
            self.distance_history.pop(0)
        if self.distance_history:
            self.smoothed_distance = sum(self.distance_history) / len(self.distance_history)
        
        self.prev_angle = self.smoothed_angle
        self.angle_history.append(raw_angle)
        if len(self.angle_history) > self.config.smoothing_window:
            self.angle_history.pop(0)
        if self.angle_history:
            self.smoothed_angle = sum(self.angle_history) / len(self.angle_history)

    def _get_angle_delta(self) -> float:
        delta = self.smoothed_angle - self.prev_angle
        return 0 if abs(delta) > 0.3 else delta

    def _can_gesture(self) -> bool:
        return (self.current_time - self.last_trigger_time) > self.config.cooldown_frames

    def _on_triggered(self):
        self.last_trigger_time = self.current_time

    def reset(self):
        self.distance_history.clear()
        self.angle_history.clear()
        self.smoothed_distance = 0
        self.last_trigger_time = -1000

