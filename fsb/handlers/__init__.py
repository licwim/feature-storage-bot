# !/usr/bin/env python

import logging

from fsb.events.common import (
    EventDTO, CommandEventDTO, MentionEventDTO, MenuEventDTO, ChatActionEventDTO, MessageEventDTO
)
from fsb.services import FoolService
from fsb.telegram.client import TelegramApiClient


class Handler:
    event_class = EventDTO

    def __init__(self, event: EventDTO, client: TelegramApiClient):
        assert isinstance(event, self.event_class)
        self.client = client
        self.logger = logging.getLogger('main')
        for attr, value in event.get_attributes().items():
            setattr(self, attr, value)

    async def run(self):
        self.logger.info(f"Run handler {self.__class__.__name__}")


class CommandHandler(Handler, CommandEventDTO):
    event_class = CommandEventDTO


class MentionHandler(Handler, MentionEventDTO):
    event_class = MentionEventDTO

    MENTION_NAME_USERNAME = 'username'
    MENTION_NAME_FIRSTNAME = 'firstname'
    MENTION_NAME_RANK = 'rank'
    MENTION_NAME_NONE = 'none'
    MENTION_NAME_UNKNOWN = 'unknown'

    MESSAGE_MENTION_LIMIT = 141

    def get_members_mentions(self, members: list, mention_type: str = MENTION_NAME_USERNAME) -> list:
        members_mentions = []

        for member in members:
            order = []
            mention_link = f"[{{member_name}}](tg://user?id={str(member.id)})"
            member_names = {
                self.MENTION_NAME_USERNAME: (member.username, '@{member_name}'),
                self.MENTION_NAME_FIRSTNAME: member.first_name,
                self.MENTION_NAME_RANK: member.participant.rank if hasattr(member.participant, 'rank') else None,
                self.MENTION_NAME_NONE: '\u200b',
                self.MENTION_NAME_UNKNOWN: 'ты'
            }

            match mention_type:
                case self.MENTION_NAME_FIRSTNAME:
                    order = [self.MENTION_NAME_FIRSTNAME, self.MENTION_NAME_USERNAME]
                case self.MENTION_NAME_RANK:
                    order = [self.MENTION_NAME_RANK, self.MENTION_NAME_USERNAME, self.MENTION_NAME_FIRSTNAME]
                case self.MENTION_NAME_NONE:
                    order = [self.MENTION_NAME_NONE]
                case _:
                    order = [self.MENTION_NAME_USERNAME, self.MENTION_NAME_FIRSTNAME]

            order.append(self.MENTION_NAME_UNKNOWN)

            for order_mention_type in order:
                member_name = member_names[order_mention_type]
                template = mention_link

                if isinstance(member_name, tuple):
                    member_name, template = member_name

                if member_name:
                    members_mentions.append(template.format(member_name=member_name))
                    break

        return members_mentions


class MenuHandler(Handler, MenuEventDTO):
    event_class = MenuEventDTO
    INPUT_TIMEOUT = 60

    async def action_close_general_menu(self):
        await self.menu_message.delete()


class ChatActionHandler(Handler, ChatActionEventDTO):
    event_class = ChatActionEventDTO


class FoolHandler(Handler, MessageEventDTO):
    async def run(self):
        await super().run()
        await FoolService(self.client).send_message(self.chat)
