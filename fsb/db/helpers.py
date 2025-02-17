# !/usr/bin/env python


class DirtyModel:
    def __init__(self, dirty_state):
        self._dirty_state = dirty_state

    def __enter__(self):
        return self._dirty_state.on()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._dirty_state.out()


class DirtyModelState:
    active = False

    def is_dirty(self):
        return self.active

    def on(self):
        self.active = True
        return self

    def out(self):
        self.active = False
        return self
