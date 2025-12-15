"""Core module for Christmas Hologram."""

from .core_hand_tracking import HandDetector
from .gesture_controller import GestureController, GestureConfig
from .state_manager import StateManager, AppState

__all__ = [
    "HandDetector",
    "GestureController",
    "GestureConfig",
    "StateManager",
    "AppState",
]
