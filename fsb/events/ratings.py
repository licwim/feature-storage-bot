# !/usr/bin/env python

from typing import Union

from telethon import Button

from fsb.db.models import QueryEvent, Rating, Member, RatingMember


class RatingQueryEvent(QueryEvent):
    def __init__(self, sender_id: int = None, rating_id: int = None, member_id: int = None, rating_member_id: int = None):
        self.rating_id = rating_id
        self.rating = None
        self.member_id = member_id
        self.member = None
        self.rating_member_id = rating_member_id
        self.rating_member = None
        super().__init__(sender_id, self.build_data_dict())

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
        sender_id = data_dict['sender_id']
        data = data_dict['data']
        return cls(
            sender_id=sender_id,
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
    def get_message_and_buttons(sender_id, ratings_list) -> tuple:
        if ratings_list:
            text = "**Список твоих рейтингов:**\n" + '\n'.join(ratings_list)
        else:
            text = "Список твоих рейтингов пуст"
        buttons = [
            [
                Button.inline("Зарегаться", RegMenuRatingEvent(sender_id).save_get_id()),
                Button.inline("Разрегаться", UnregMenuRatingEvent(sender_id).save_get_id())
            ],
            [
                Button.inline("Создать рейтинг", CreateRatingEvent(sender_id).save_get_id()),
                Button.inline("Список рейтингов", ListRatingEvent(sender_id).save_get_id()),
            ],
            [
                Button.inline("Закрыть", CloseGeneralMenuRatingEvent(sender_id).save_get_id())
            ]
        ]
        return text, buttons


class RegRatingEvent(RatingQueryEvent):
    pass


class UnregRatingEvent(RatingQueryEvent):
    pass


class RegMenuRatingEvent(RatingQueryEvent):
    pass


class UnregMenuRatingEvent(RatingQueryEvent):
    pass


class CloseGeneralMenuRatingEvent(RatingQueryEvent):
    pass


class ListRatingEvent(RatingQueryEvent):
    pass


class CreateRatingEvent(RatingQueryEvent):
    pass


class DeleteRatingEvent(RatingQueryEvent):
    pass


class ChangeRatingEvent(RatingQueryEvent):
    pass


class MenuRatingEvent(RatingQueryEvent):
    pass
