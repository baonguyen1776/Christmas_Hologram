"""
State Manager - Simple state machine for app states
"""

from enum import Enum, auto
from typing import Callable, Dict, List


class AppState(Enum):
    TREE = auto()
    EXPANDING = auto()
    UNIVERSE = auto()
    COLLAPSING = auto()
    PHOTO_ZOOM = auto()


class StateManager:
    def __init__(self):
        self.current_state = AppState.TREE
        self.lock_frames = 0
        self.enter_callbacks: Dict[AppState, List[Callable]] = {s: [] for s in AppState}
        self.exit_callbacks: Dict[AppState, List[Callable]] = {s: [] for s in AppState}

    def on_enter(self, state: AppState, callback: Callable):
        self.enter_callbacks[state].append(callback)

    def on_exit(self, state: AppState, callback: Callable):
        self.exit_callbacks[state].append(callback)

    def transition_to(self, new_state: AppState, lock_frames: int = 0):
        if self.lock_frames > 0:
            return
        
        old_state = self.current_state
        for cb in self.exit_callbacks[old_state]:
            cb()
        
        self.current_state = new_state
        self.lock_frames = lock_frames
        
        for cb in self.enter_callbacks[new_state]:
            cb()

    def update(self):
        if self.lock_frames > 0:
            self.lock_frames -= 1

    def is_tree(self) -> bool:
        return self.current_state == AppState.TREE

    def is_universe(self) -> bool:
        return self.current_state == AppState.UNIVERSE

    def is_zoomed(self) -> bool:
        return self.current_state == AppState.PHOTO_ZOOM

    def is_state(self, state: AppState) -> bool:
        return self.current_state == state
