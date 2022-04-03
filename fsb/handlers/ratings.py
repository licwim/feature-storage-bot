# !/usr/bin/env python

from typing import Union

from inflection import underscore
from telethon.tl.custom.button import Button

from fsb.db.models import Member
from fsb.db.models import QueryEvent
from fsb.db.models import Rating
from fsb.db.models import RatingMember
from fsb.handlers import BaseMenu
from fsb.handlers import Handler
from fsb.handlers.commands import BaseCommand
from fsb.telegram.client import TelegramApiClient


class RatingQueryEvent(QueryEvent):
    def __init__(self, sender: int = None, rating_id: int = None, member_id: int = None, rating_member_id: int = None):
        self.rating_id = rating_id
        self.rating = None
        self.member_id = member_id
        self.member = None
        self.rating_member_id = rating_member_id
        self.rating_member = None
        super().__init__(sender, self.build_data_dict())

    def build_data_dict(self) -> dict:
        return {
            'rating_id': self.rating_id,
            'member_id': self.member_id,
            'rating_member_id': self.rating_member_id,
        }

    @classmethod
    def normalize_data_dict(cls, data_dict: dict) -> dict:
        data_dict = super().normalize_data_dict(data_dict)
        for key in ['rating_id', 'member_id', 'rating_member_id']:
            if key not in data_dict['data']:
                data_dict['data'][key] = None
        return data_dict

    @classmethod
    def from_dict(cls, data_dict: dict) -> QueryEvent:
        data_dict = cls.normalize_data_dict(data_dict)
        sender = data_dict['sender']
        data = data_dict['data']
        return cls(
            sender=sender,
            rating_id=data['rating_id'],
            member_id=data['member_id'],
            rating_member_id=data['rating_member_id']
        )

    def get_rating(self) -> Union[Rating, None]:
        if not self.rating and self.rating_id:
            self.rating = Rating.get_by_id(self.rating_id)

        return self.rating

    def get_member(self) -> Union[Member, None]:
        if not self.member and self.member_id:
            self.member = Member.get_by_id(self.member_id)

        return self.member

    def get_rating_member(self) -> Union[RatingMember, None]:
        if not self.rating_member and self.rating_member_id:
            self.rating_member = RatingMember.get_by_id(self.rating_member_id)

        return self.rating_member


class GeneralMenuRatingEvent(RatingQueryEvent):
    @staticmethod
    def get_message_and_buttons(sender) -> tuple:
        return "Меню рейтингов", [
            [
                Button.inline('Список рейтингов', ListRatingEvent(sender).save_get_id())
            ],
            [
                Button.inline('Создать рейтинг', CreateRatingEvent(sender).save_get_id()),
                Button.inline('Удалить рейтинг', DeleteMenuRatingEvent(sender).save_get_id()),
            ]
        ]
    
    
class CreateRatingEvent(RatingQueryEvent):
    pass


class ListRatingEvent(RatingQueryEvent):
    pass


class DeleteMenuRatingEvent(RatingQueryEvent):
    pass


class MenuRatingEvent(RatingQueryEvent):
    pass


class DeleteRatingEvent(RatingQueryEvent):
    pass


class ChangeRatingEvent(RatingQueryEvent):
    pass


class ListMembersRatingEvent(RatingQueryEvent):
    pass


class RatingsSettingsCommand(BaseCommand):
    def __init__(self, client: TelegramApiClient):
        super().__init__(client, 'ratings')
        self._area = self.ONLY_CHAT

    @Handler.handle_decorator
    async def handle(self, event):
        await super().handle(event)
        text, buttons = GeneralMenuRatingEvent.get_message_and_buttons(event.message.sender.id)
        await self._client.send_message(self.entity, text, buttons=buttons)


class RatingCommand(BaseCommand):
    def __init__(self, client: TelegramApiClient):
        super().__init__(client, 'rating')
        self._area = self.ONLY_CHAT


class RatingsSettingsQuery(BaseMenu):
    def __init__(self, client: TelegramApiClient):
        super().__init__(client)
        self._area = self.ONLY_CHAT

    async def handle(self, event):
        await super().handle(event)
        assert isinstance(self.query_event, RatingQueryEvent)

        query_event_type = underscore(self.query_event.__class__.__name__.replace('RoleEvent', ''))
        action = getattr(self, 'action_' + query_event_type)
        if action:
            await action()
