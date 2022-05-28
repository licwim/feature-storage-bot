# !/usr/bin/env python

from fsb.telegram.client import TelegramApiClient


class Factory:
    _available_classes = []

    def __init__(self, client: TelegramApiClient, available_classes: list):
        self._objects = {}
        self._client = client
        self._loop = client.loop
        self._available_classes = available_classes

    def create_all(self):
        for cls in self._available_classes:
            self.create_object(cls)

    def create_object(self, cls):
        if cls in self._available_classes:
            obj = cls(self._client)
            self.add_object(obj)
            return self.get_object(cls)
        return None

    def add_object(self, obj) -> bool:
        if obj.__class__ not in self._objects.keys():
            self._objects[obj.__class__] = obj
            return True
        return False

    def get_object(self, key):
        if key in self._objects.keys():
            return self._objects[key]
        return None

    def get_objects(self) -> dict:
        return self._objects
