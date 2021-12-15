# !/usr/bin/env python

import keyboard


class InputListener:

    events_list = {}

    def __init__(self):
        # Перехватываются глобальные нажатия клавиш, что  как-то чересчур. Пока что выключил input listener
        # keyboard.hook(self._on_key)
        pass

    def _on_key(self, event):
        if event.event_type == 'down':
            if event.name == 'esc':
                self.stop()
            elif event.name == 'i':
                self._input()
            else:
                return

    def add_event(self, name: str, event: callable):
        if name and event and name not in self.events_list:
            self.events_list.update({name: event})

    def _input(self):
        input_string = input()
        if (input_string in ['stop', 'exit', 'quit']) & ('exit' in self.events_list):
            self.events_list['exit']()

    def stop(self):
        if 'exit' in self.events_list:
            self.events_list['exit']()
        keyboard.unhook_all()
