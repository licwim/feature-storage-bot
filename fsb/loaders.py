# !/usr/bin/env python

from fsb.config import config
from fsb.controllers import (
    Controller, CommandController, MentionController, MenuController, ChatActionController, FoolCommandController,
    FoolMentionController
)
from fsb.factories import ControllerFactory
from fsb.telegram.client import TelegramApiClient


class Loader:
    _loaded_classes = []
    _loaded_objects = {}

    def create_objects(self):
        for cls in self._loaded_classes:
            obj = self._create_object(cls)
            self._loaded_objects[cls.__name__] = obj

    def _create_object(self, cls) -> object:
        pass

    def run_objects(self):
        for obj in self._loaded_objects.values():
            self._run_object(obj)

    def _run_object(self, obj):
        pass


class ControllerLoader(Loader):
    _loaded_classes = [
        CommandController,
        MentionController,
        MenuController,
        ChatActionController
    ]

    _fool_loaded_classes = [
        ChatActionController,
        FoolCommandController,
        FoolMentionController
    ]

    def __init__(self, client: TelegramApiClient):
        self._client = client
        self._init_fool()
        self.create_objects()

    def _init_fool(self):
        if config.FOOL_DAY:
            self._loaded_classes = self._fool_loaded_classes

    def _create_object(self, cls) -> Controller:
        return ControllerFactory(cls, self._client).create_object()

    def _run_object(self, obj: Controller):
        obj.listen()
