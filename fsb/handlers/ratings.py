# !/usr/bin/env python

import random
from asyncio import sleep
from datetime import datetime
from typing import Union

from inflection import underscore
from peewee import DoesNotExist
from peewee import JOIN
from telethon.tl.custom.button import Button

from fsb.db.models import Chat
from fsb.db.models import Member
from fsb.db.models import QueryEvent
from fsb.db.models import Rating
from fsb.db.models import RatingMember
from fsb.db.models import User
from fsb.handlers import BaseMenu, ChatActionHandler
from fsb.handlers import Handler
from fsb.handlers.commands import BaseCommand
from fsb.helpers import Helper
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
    def get_message_and_buttons(sender, ratings_list) -> tuple:
        if ratings_list:
            text = "**Список твоих рейтингов:**\n" + '\n'.join(ratings_list)
        else:
            text = "Список твоих рейтингов пуст"
        buttons = [
            Button.inline("Зарегаться", RegMenuRatingEvent(sender).save_get_id()),
            Button.inline("Разрегаться", UnregMenuRatingEvent(sender).save_get_id())
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


class CreateRatingsOnJoinChat(ChatActionHandler):
    def __init__(self, client: TelegramApiClient):
        super().__init__(client)

    @Handler.handle_decorator
    async def handle(self, event):
        if not event.user_joined and not event.user_added:
            return
        await super().handle(event)
        chat = Chat.get_or_create(
            telegram_id=self.entity.id,
            defaults={
                'name': self.entity.title,
                'type': Chat.get_chat_type(self.entity)
            }
        )[0]
        Rating.get_or_create(
            name='pidor',
            chat=chat,
            defaults={
                'command': 'pidor'
            }
        )
        Rating.get_or_create(
            name='chad',
            chat=chat,
            defaults={
                'command': 'chad'
            }
        )


class RatingsSettingsCommand(BaseCommand):
    def __init__(self, client: TelegramApiClient):
        super().__init__(client, 'ratings')
        self._area = self.ONLY_CHAT

    @Handler.handle_decorator
    async def handle(self, event):
        await super().handle(event)
        try:
            ratings = Rating.select().join(RatingMember).where(
                RatingMember.member == Member.get(
                    Member.user == User.get(User.telegram_id == self.event.message.sender.id),
                    Member.chat == Chat.get(Chat.telegram_id == self.entity.id)
                ),
            )
            ratings_list = [rating.name for rating in ratings]
        except DoesNotExist:
            ratings_list = []
        text, buttons = GeneralMenuRatingEvent.get_message_and_buttons(event.message.sender.id, ratings_list)
        await self._client.send_message(self.entity, text, buttons=buttons)


class RatingCommand(BaseCommand):
    PIDOR_COMMAND = 'pidor'
    CHAD_COMMAND = 'chad'

    PIDOR_RUN_MESSAGES = [
        'Эники-беники ели вареники',
        'Эники-беники - клёц!',
        'Вышел весёлый матрос!',
        'Ты пидор.'
    ]

    CHAD_RUN_MESSAGES = [
        'Эне, бене, раба,',
        'Квинтер, финтер, жаба.',
        'Эне, бене, рес,',
        'Квинтер, финтер, жес!'
    ]

    WINNER_MESSAGE_PATTERN = "Сегодня {msg_name} дня - {member_name}!"

    def __init__(self, client: TelegramApiClient):
        super().__init__(client, [self.PIDOR_COMMAND, self.CHAD_COMMAND])
        self._area = self.ONLY_CHAT

    @Handler.handle_decorator
    async def handle(self, event):
        await super().handle(event)

        match self.command:
            case self.PIDOR_COMMAND:
                rating_name = 'pidor'
                msg_name = 'ПИДОР'
                run_messages = self.PIDOR_RUN_MESSAGES
            case self.CHAD_COMMAND:
                rating_name = 'chad'
                msg_name = 'КРАСАВЧИК'
                run_messages = self.CHAD_RUN_MESSAGES
            case _:
                raise RuntimeError
        rating = Rating.get_or_create(
            name=rating_name,
            chat=Chat.get(Chat.telegram_id == self.entity.id),
            defaults={
                'command': rating_name
            }
        )[0]

        rating_members = await self.get_rating_members(rating)
        if not rating_members:
            return

        if not rating.last_run or rating.last_run < datetime.today().replace(hour=0, minute=0, second=0, microsecond=0):
            random.seed()
            pos = random.randint(0, len(rating_members) - 1)
            tg_member, db_member = rating_members[pos]
            db_member.times += 1
            db_member.save()
            rating.last_winner = db_member.member
            rating.last_run = datetime.now()
            rating.save()
            message = await self._client._client.send_message(entity=self.entity, message='Итаааааак...')
            await sleep(1)
            for text in run_messages:
                await message.edit(text)
                await sleep(1)
            await message.edit(self.WINNER_MESSAGE_PATTERN.format(
                msg_name=msg_name,
                member_name=Helper.make_member_name(tg_member, with_mention=True)
            ))
        else:
            assert rating.last_winner
            tg_member = db_member = None
            for rating_member in rating_members:
                tg_member, db_member = rating_member
                if rating.last_winner == db_member.member:
                    break
            await self._client.send_message(self.entity, self.WINNER_MESSAGE_PATTERN.format(
                msg_name=msg_name,
                member_name=Helper.make_member_name(tg_member, with_mention=True)
            ))

    async def get_rating_members(self, rating: Rating) -> list:
        actual_members = await self._client.get_dialog_members(self.entity)
        rating_members = RatingMember.select().where(RatingMember.rating == rating)
        db_members = {}
        for rating_member in rating_members:
            db_members[rating_member.member.user.telegram_id] = rating_member

        result = []
        for tg_member in actual_members:
            if tg_member.id in db_members:
                result.append((tg_member, db_members[tg_member.id]))
        return result


class RatingsSettingsQuery(BaseMenu):
    def __init__(self, client: TelegramApiClient):
        super().__init__(client)
        self._area = self.ONLY_CHAT

    async def handle(self, event):
        await super().handle(event)
        if not isinstance(self.query_event, RatingQueryEvent):
            return

        query_event_type = underscore(self.query_event.__class__.__name__.replace('RatingEvent', ''))
        action = getattr(self, 'action_' + query_event_type)
        if action:
            await action()

    async def action_general_menu(self):
        try:
            ratings = Rating.select().join(RatingMember).where(
                RatingMember.member == Member.get(
                    Member.user == User.get(User.telegram_id == self._sender),
                    Member.chat == Chat.get(Chat.telegram_id == self.entity.id)
                ),
            )
            ratings_list = [rating.name for rating in ratings]
        except DoesNotExist:
            ratings_list = []
        text, buttons = GeneralMenuRatingEvent.get_message_and_buttons(self._sender, ratings_list)
        await self._menu_message.edit(text, buttons=buttons)

    async def action_reg_menu(self):
        member = Member.get(
            Member.user == User.get(User.telegram_id == self._sender),
            Member.chat == Chat.get(Chat.telegram_id == self.entity.id)
        )
        ratings = Rating.select().join(RatingMember, JOIN.LEFT_OUTER).where(
            ((RatingMember.member != member)
             | (RatingMember.member.is_null()))
            & ((Rating.chat == Chat.get(Chat.telegram_id == self.entity.id))
               | (Rating.chat.is_null()))
        )

        buttons = []
        buttons_line = []
        for rating in ratings:
            buttons_line.append(Button.inline(
                f"{rating.name}",
                RegRatingEvent(sender=self._sender, rating_id=rating.id, member_id=member.id).save_get_id()
            ))
            if len(buttons_line) == 2:
                buttons.append(buttons_line.copy())
                buttons_line = []
        if buttons_line:
            buttons.append(buttons_line.copy())
        buttons.append([Button.inline("<< К меню рейтингов", GeneralMenuRatingEvent(self._sender).save_get_id())])
        await self._menu_message.edit("Куда регаться", buttons=buttons)

    async def action_reg(self):
        rating = self.query_event.get_rating()
        member = self.query_event.get_member()
        rating_member = RatingMember.get_or_none(
            RatingMember.rating == rating,
            RatingMember.member == member
        )
        if rating_member:
            await self._client.send_message(self.entity, "Ты уже зареган")
            return
        else:
            RatingMember.create(rating=rating, member=member)
            tg_member = await self._client.get_entity(member.user.telegram_id)
            await self._client.send_message(
                self.entity,
                f"{tg_member.first_name} теперь зареган в {rating.name}"
            )
