# !/usr/bin/env python

from fsb import logger
from fsb.events.common import EventDTO, CommandEventDTO, MentionEventDTO, MenuEventDTO, ChatActionEventDTO
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


class MentionHandler(Handler, MentionEventDTO):
    event_class = MentionEventDTO
    UNKNOWN_NAME_REPLACEMENT = "ты"

    def get_members_mentions(self, members: list, rank_mention: bool = False) -> list:
        members_mentions = []

        for member in members:
            rank = None

            if rank_mention:
                try:
                    rank = member.participant.rank
                except AttributeError:
                    pass

            if rank:
                members_mentions.append(f"[{rank}](tg://user?id={str(member.id)})")
            elif member.username:
                members_mentions.append('@' + member.username)
            else:
                member_name = member.first_name if member.first_name else self.UNKNOWN_NAME_REPLACEMENT
                members_mentions.append(f"[{member_name}](tg://user?id={str(member.id)})")

        return members_mentions


class MenuHandler(Handler, MenuEventDTO):
    event_class = MenuEventDTO
    INPUT_TIMEOUT = 60

    async def action_close_general_menu(self):
        await self.menu_message.delete()


class ChatActionHandler(Handler, ChatActionEventDTO):
    event_class = ChatActionEventDTO
