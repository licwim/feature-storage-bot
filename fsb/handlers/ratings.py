# !/usr/bin/env python

import random
from asyncio import sleep
from datetime import datetime
from typing import Union

from inflection import underscore
from peewee import DoesNotExist
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

PIDOR_KEYWORD = 'pidor'
CHAD_KEYWORD = 'chad'
LANGS = {
    'pidor': {
        'en': 'pidor',
        'ru': 'пидор',
    },
    'chad': {
        'en': 'chad',
        'ru': 'красавчик'
    }
}


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

        chat = Chat.get(telegram_id=self.entity.id)

        Rating.get_or_create(
            name=PIDOR_KEYWORD,
            chat=chat,
            defaults={
                'command': PIDOR_KEYWORD
            }
        )

        Rating.get_or_create(
            name=CHAD_KEYWORD,
            chat=chat,
            defaults={
                'command': CHAD_KEYWORD
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
            ratings = Rating.select().join(RatingMember, on=(RatingMember.rating_id == Rating.id)).where(
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
    MESSAGE_WAIT = 2
    PIDOR_COMMAND = PIDOR_KEYWORD
    CHAD_COMMAND = CHAD_KEYWORD

    PIDOR_RUN_MESSAGES = [
        "Вышел месяц из тумана,",
        "Вынул ножик из кармана.",
        "Буду резать, буду бить,",
        "Всё равно ты пидор!",
    ]

    CHAD_RUN_MESSAGES = [
        "Сидел король на лавочке,",
        "Считал свои булавочки:",
        "«Раз, два, три»",
        "Королевой будешь ты!",
    ]

    WINNER_MESSAGE_PATTERN = "Сегодня {msg_name} дня - {member_name}!"

    def __init__(self, client: TelegramApiClient):
        super().__init__(client, [self.PIDOR_COMMAND, self.CHAD_COMMAND])
        self._area = self.ONLY_CHAT

    @Handler.handle_decorator
    async def handle(self, event):
        await super().handle(event)
        self.set_wait(True)

        match self.command:
            case self.PIDOR_COMMAND:
                rating_name = PIDOR_KEYWORD
                msg_name = LANGS[PIDOR_KEYWORD]['ru'].upper()
                run_messages = self.PIDOR_RUN_MESSAGES
            case self.CHAD_COMMAND:
                rating_name = CHAD_KEYWORD
                msg_name = LANGS[CHAD_KEYWORD]['ru'].upper()
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

        actual_members = await self._client.get_dialog_members(self.entity)
        rating_members = RatingMember.select().where(RatingMember.rating == rating)
        members_collection = Helper.collect_members(actual_members, rating_members)
        if not members_collection:
            return

        if rating.last_winner \
                and rating.last_run \
                and rating.last_run >= datetime.today().replace(hour=0, minute=0, second=0, microsecond=0):
            try:
                assert rating.last_winner
                tg_member = db_member = None
                for member in members_collection:
                    tg_member, db_member = member
                    if rating.last_winner == db_member:
                        break
                member_name = Helper.make_member_name(tg_member)
            except DoesNotExist or AssertionError:
                member_name = "__какой-то неизвестный хер__"
            await self._client.send_message(self.entity, self.WINNER_MESSAGE_PATTERN.format(
                msg_name=msg_name,
                member_name=member_name
            ))
        else:
            random.seed()
            pos = random.randint(0, len(members_collection) - 1)
            tg_member, db_member = members_collection[pos]
            db_member.count += 1
            db_member.save()
            rating.last_winner = db_member
            rating.last_run = datetime.now()
            rating.save()
            message = await self._client._client.send_message(entity=self.entity, message='Итаааааак...')
            await sleep(self.MESSAGE_WAIT)
            text = ''
            for line in run_messages:
                text += line + '\n'
                await message.edit(text)
                await sleep(self.MESSAGE_WAIT)
            await self._client.send_message(self.entity, self.WINNER_MESSAGE_PATTERN.format(
                msg_name=msg_name,
                member_name=Helper.make_member_name(tg_member, with_mention=True)
            ))
        self.set_wait(False)


class StatRatingCommand(BaseCommand):
    PIDOR_STAT_COMMAND = RatingCommand.PIDOR_COMMAND + 'stat'
    CHAD_STAT_COMMAND = RatingCommand.CHAD_COMMAND + 'stat'

    def __init__(self, client: TelegramApiClient):
        super().__init__(client, [self.PIDOR_STAT_COMMAND, self.CHAD_STAT_COMMAND])
        self._area = self.ONLY_CHAT

    @Handler.handle_decorator
    async def handle(self, event):
        await super().handle(event)

        match self.command:
            case self.PIDOR_STAT_COMMAND:
                rating_name = PIDOR_KEYWORD
                msg_name = 'ПИДОР'
            case self.CHAD_STAT_COMMAND:
                rating_name = CHAD_KEYWORD
                msg_name = 'КРАСАВЧИК'
            case _:
                raise RuntimeError
        rating = Rating.get_or_create(
            name=rating_name,
            chat=Chat.get(Chat.telegram_id == self.entity.id),
            defaults={
                'command': rating_name
            }
        )[0]

        actual_members = await self._client.get_dialog_members(self.entity)
        rating_members = RatingMember.select().where(RatingMember.rating == rating).order_by(RatingMember.count.desc())
        members_collection = Helper.collect_members(actual_members, rating_members)
        if not members_collection:
            return

        message = f"**Результаты {msg_name} Дня**\n"
        pos = 1
        for member in members_collection:
            tg_member, db_member = member
            message += f"#**{str(pos)}**   " \
                       f"{Helper.make_member_name(tg_member)} - " \
                       f"{Helper.make_count_str(db_member.count)}\n"
            pos += 1
        await self._client.send_message(self.entity, message)


class RatingsSettingsQuery(BaseMenu):
    def __init__(self, client: TelegramApiClient):
        super().__init__(client, RatingQueryEvent)
        self._area = self.ONLY_CHAT

    @Handler.handle_decorator
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
            ratings = Rating.select().join(RatingMember, on=(RatingMember.rating_id == Rating.id)).where(
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
        chat = Chat.get(Chat.telegram_id == self.entity.id)
        member = Member.get(
            Member.user == User.get(User.telegram_id == self._sender),
            Member.chat == chat
        )
        chat_ratings = list(Rating.select().where(Rating.chat == chat).execute())
        member_ratings = list(Rating.select().join(RatingMember, on=(RatingMember.rating_id == Rating.id)).where(
            Rating.chat == chat,
            RatingMember.member == member
        ).execute())
        ratings = list(set(chat_ratings) - set(member_ratings))

        buttons = []
        for rating in ratings:
            buttons.append((
                f"{rating.name}",
                RegRatingEvent(sender=self._sender, rating_id=rating.id, member_id=member.id).save_get_id()
            ))
        buttons = Helper.make_buttons_layout(buttons, (
            "<< К меню рейтингов",
            GeneralMenuRatingEvent(self._sender).save_get_id()
        ))

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

    async def action_unreg_menu(self):
        chat = Chat.get(Chat.telegram_id == self.entity.id)
        member = Member.get(
            Member.user == User.get(User.telegram_id == self._sender),
            Member.chat == chat
        )
        ratings = Rating.select().join(RatingMember, on=(RatingMember.rating_id == Rating.id)).where(
            Rating.chat == chat,
            RatingMember.member == member
        )

        buttons = []
        for rating in ratings:
            buttons.append((
                f"{rating.name}",
                UnregRatingEvent(sender=self._sender, rating_id=rating.id, member_id=member.id).save_get_id()
            ))
        buttons = Helper.make_buttons_layout(buttons, (
            "<< К меню рейтингов",
            GeneralMenuRatingEvent(self._sender).save_get_id()
        ))

        await self._menu_message.edit("Откуда разрегаться", buttons=buttons)

    async def action_unreg(self):
        rating = self.query_event.get_rating()
        member = self.query_event.get_member()
        rating_member = RatingMember.get_or_none(
            RatingMember.rating == rating,
            RatingMember.member == member
        )
        if rating_member:
            rating_member.delete_instance()
            tg_member = await self._client.get_entity(member.user.telegram_id)
            await self._client.send_message(
                self.entity,
                f"{tg_member.first_name} теперь разреган из {rating.name}"
            )
        else:
            await self._client.send_message(self.entity, "Ты уже разреган")
            return
