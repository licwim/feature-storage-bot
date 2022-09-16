# !/usr/bin/env python

from fsb import logger
from fsb.events.common import EventDTO, CommandEventDTO, WatcherEventDTO, MenuEventDTO, ChatActionEventDTO
from fsb.telegram.client import TelegramApiClient


class Handler:
    event_class = EventDTO

    def __init__(self, event: EventDTO, client: TelegramApiClient):
        assert isinstance(event, self.event_class)
        self.client = client
        for attr, value in event.get_attributes().items():
            setattr(self, attr, value)

    async def run(self):
        logger.info(f"Run handler {self.__class__.__name__}")


class CommandHandler(Handler, CommandEventDTO):
    event_class = CommandEventDTO


class WatcherHandler(Handler, WatcherEventDTO):
    event_class = WatcherEventDTO


class MenuHandler(Handler, MenuEventDTO):
    event_class = MenuEventDTO
    INPUT_TIMEOUT = 60

    async def action_close_general_menu(self):
        await self.menu_message.delete()


class ChatActionHandler(Handler, ChatActionEventDTO):
    event_class = ChatActionEventDTO
