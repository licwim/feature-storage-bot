# !/usr/bin/env python

from .handlers import Handler
from .handlers.commands import EntityInfoCommand
from .handlers.commands import PingCommand
from .handlers.commands import StartCommand
from .handlers.watchers import MentionWatcher
from .telegram.client import TelegramApiClient


class HandlersController:
    _available_handlers = [
        StartCommand,
        PingCommand,
        MentionWatcher,
        EntityInfoCommand,
    ]

    def __init__(self, client: TelegramApiClient):
        self._handlers = {}
        self._client = client
        self._loop = client.loop
        for handler in self._available_handlers:
            self.create_handler(handler)

    def create_handler(self, handler_class):
        if handler_class in self._available_handlers:
            handler = handler_class(self._client)
            return self.add_handler(handler)
        return False

    def add_handler(self, handler: Handler):
        if handler.__class__ not in self._handlers.keys():
            self._handlers[handler.__class__] = handler
            handler.listen()
            return True
        return False

    def get_handler(self, key):
        if key in self._handlers.keys():
            return self._handlers[key]
        return False
