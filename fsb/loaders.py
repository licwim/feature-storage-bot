# !/usr/bin/env python

from fsb.controllers import Controller, CommandController, WatcherController, MenuController, ChatActionController
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
        WatcherController,
        MenuController,
        ChatActionController
    ]

    def __init__(self, client: TelegramApiClient):
        self._client = client
        self.create_objects()

    def _create_object(self, cls) -> Controller:
        return ControllerFactory(cls, self._client).create_object()

    def _run_object(self, obj: Controller):
        obj.listen()
