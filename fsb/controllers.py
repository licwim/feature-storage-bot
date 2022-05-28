# !/usr/bin/env python

from fsb.factories import Factory
from fsb.handlers.commands import AboutInfoCommand
from fsb.handlers.commands import EntityInfoCommand
from fsb.handlers.commands import PingCommand
from fsb.handlers.commands import StartCommand
from fsb.handlers.pipelines import JoinChatPipeline
from fsb.handlers.ratings import RatingCommand
from fsb.handlers.ratings import RatingsSettingsCommand
from fsb.handlers.ratings import RatingsSettingsQuery
from fsb.handlers.ratings import StatRatingCommand
from fsb.handlers.roles import RolesSettingsCommand
from fsb.handlers.roles import RolesSettingsQuery
from fsb.handlers.watchers import MentionWatcher
from fsb.telegram.client import TelegramApiClient


class Controller:
    def __init__(self, client: TelegramApiClient, factory: Factory, run_command: str):
        self.objects = {}
        self._client = client
        self._factory = factory
        self._run_command = run_command

    def object_run(self, obj):
        action = getattr(obj, self._run_command)
        if action:
            action()

    def all_objects_run(self):
        self._factory.create_all()
        for obj in self._factory.get_objects().values():
            self.object_run(obj)
            self.objects[obj.__class__] = obj


class GeneralHandlersController(Controller):
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
        JoinChatPipeline,
    ]

    def __init__(self, client: TelegramApiClient):
        factory = Factory(client, self._available_handlers)
        super().__init__(client, factory, 'listen')
