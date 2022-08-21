# !/usr/bin/env python

from typing import Type

from fsb.controllers import Controller
from fsb.telegram.client import TelegramApiClient


class Factory:
    def __init__(self, class_object: Type):
        self.cls = class_object

    def create_object(self):
        pass


class ControllerFactory(Factory):
    def __init__(self, controller_class: Type[Controller], client: TelegramApiClient):
        assert issubclass(controller_class, Controller)
        super().__init__(controller_class)
        self._client = client
        self._loop = client.loop

    def create_object(self) -> Controller:
        return self.cls(self._client)
