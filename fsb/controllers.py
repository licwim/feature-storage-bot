# !/usr/bin/env python

from fsb.handlers import Handler
from fsb.handlers.commands import AboutInfoCommand
from fsb.handlers.commands import EntityInfoCommand
from fsb.handlers.commands import PingCommand
from fsb.handlers.commands import StartCommand
from fsb.handlers.ratings import RatingCommand, CreateRatingsOnJoinChat, StatRatingCommand
from fsb.handlers.ratings import RatingsSettingsCommand
from fsb.handlers.ratings import RatingsSettingsQuery
from fsb.handlers.roles import RolesSettingsCommand
from fsb.handlers.roles import RolesSettingsQuery
from fsb.handlers.watchers import MentionWatcher
from fsb.telegram.client import TelegramApiClient


class HandlersController:
    _available_handlers = [
        StartCommand,
        PingCommand,
        MentionWatcher,
        EntityInfoCommand,
        RolesSettingsCommand,
        RolesSettingsQuery,
        AboutInfoCommand,
        RatingsSettingsCommand,
        RatingsSettingsQuery,
        RatingCommand,
        StatRatingCommand,
        CreateRatingsOnJoinChat,
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
