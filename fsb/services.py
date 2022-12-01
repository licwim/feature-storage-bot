# !/usr/bin/env python

import json
import random
from asyncio import sleep
from datetime import datetime

from peewee import DoesNotExist, fn
from telethon.tl.types import InputPeerUser, InputPeerChat, InputPeerChannel

from fsb import logger
from fsb.config import Config
from fsb.db.models import Chat, User, Member, Rating, RatingMember
from fsb.helpers import Helper
from fsb.telegram.client import TelegramApiClient


class ChatService:
    def __init__(self, client: TelegramApiClient):
        self.client = client

    async def create_chat(self, event=None, entity=None, update: bool = False):
        if event:
            entity = event.chat
            input_chat = event.input_chat.to_json()
        elif entity:
            input_chat = None
        else:
            return None

        match Chat.get_chat_type(entity):
            case Chat.USER_TYPE:
                name = entity.username
                if not input_chat:
                    input_chat = InputPeerUser(entity.id, entity.access_hash).to_json()
            case Chat.CHAT_TYPE:
                name = entity.title
                if not input_chat:
                    input_chat = InputPeerChat(entity.id).to_json()
            case Chat.CHANNEL_TYPE:
                name = entity.title
                if not input_chat:
                    input_chat = InputPeerChannel(entity.id, entity.access_hash).to_json()
            case _:
                name = None

        type = Chat.get_chat_type(entity)
        chat = Chat.get_or_create(
            telegram_id=entity.id,
            defaults={
                'name': name,
                'type': type,
                'input_peer': input_chat
            }
        )[0]

        if update:
            chat.name = name
            chat.type = type
            chat.input_peer = input_chat
            chat.save()

        for tg_member in await self.client.get_dialog_members(entity):
            user = self.create_user(entity=tg_member, update=update)
            Member.get_or_create(chat=chat, user=user)

        return chat

    def create_user(self, event=None, entity=None, update: bool = False):
        if event:
            entity = event.chat
            input_chat = json.dumps(event.input_chat.to_dict())
        elif entity:
            input_chat = InputPeerUser(entity.id, entity.access_hash).to_json()
        else:
            return None

        name = Helper.make_member_name(entity, with_username=False)
        user = User.get_or_create(
                telegram_id=entity.id,
                defaults={
                    'name': name,
                    'nickname': entity.username,
                    'phone': entity.phone,
                    'input_peer': input_chat
                }
            )[0]

        if update:
            user.name = name
            user.nickname = entity.username
            user.phone = entity.phone
            user.input_peer = input_chat
            user.save()

        return user


class RatingService:
    PIDOR_KEYWORD = 'pidor'
    PIDOR_NAME = 'пидор'
    CHAD_KEYWORD = 'chad'
    CHAD_NAME = 'красавчик'

    MESSAGE_WAIT = 2

    RUN_MESSAGE = [
        'На окне стоит бутылка,',
        'А в бутылке лимонад.',
        'Кто скорей возьмёт бутылку,',
        'Тот победе будет рад.',
    ]

    WINNER_MESSAGE_PATTERN = "Сегодня {rating_name} дня - {member_name}!"
    MONTH_WINNER_MESSAGE_PATTERN = "{rating_name} {month_name} - {member_name}!"
    UNKNOWN_PERSON = "__какой-то неизвестный хер__"
    FEW_MONTH_WINNERS_MESSAGE_PATTERN = 'В {month_name} оказалось несколько лидирующих {rating_name}, но придется выбрать одного.'

    def __init__(self, client: TelegramApiClient):
        self.client = client

    async def roll(self, rating: Rating, chat, is_month: bool = False):
        actual_members = await self.client.get_dialog_members(chat)
        rating_members = RatingMember.select().where(RatingMember.rating == rating)
        members_collection = Helper.collect_members(actual_members, rating_members)

        if not members_collection:
            return

        if is_month:
            await self._month_roll(members_collection, rating, chat)
        else:
            await self._day_roll(members_collection, rating, chat)

    async def _month_roll(self, members_collection: list, rating: Rating, chat):
        if rating.last_month_winner \
                and rating.last_month_run \
                and rating.last_month_run >= datetime.today().replace(hour=0, minute=0, second=0, microsecond=0, day=1):
            member_name = self._get_last_winner_name(rating.last_month_winner, members_collection)
            await self.client.send_message(chat, self.MONTH_WINNER_MESSAGE_PATTERN.format(
                rating_name=rating.name.upper(),
                member_name=member_name,
                month_name=Helper.get_month_name(datetime.now().month - 1, {'gent'}),
            ))
        else:
            win_count = RatingMember.select(fn.MAX(RatingMember.current_month_count))\
                .where(RatingMember.rating == rating).scalar()
            winners = []

            for tg_member, db_member in members_collection:
                if db_member.current_month_count == win_count:
                    winners.append((tg_member, db_member))

                db_member.current_month_count = 0
                db_member.save()

            winners_len = len(winners)

            if winners_len > 1:
                rating_name = Helper.inflect_word(rating.name, {'gent', 'plur'})
                await self.client\
                    .send_message(chat, self.FEW_MONTH_WINNERS_MESSAGE_PATTERN.format(
                        rating_name=rating_name.upper(),
                        month_name=Helper.get_month_name(datetime.now().month - 1, {'loct'}),
                    ))
                await self._send_rolling_message(rating, chat)
                pos = random.randint(0, winners_len - 1)
                win_tg_member, win_db_member = winners[pos]
            elif winners_len == 1:
                win_tg_member, win_db_member = winners[0]
            else:
                return

            member_name = Helper.make_member_name(win_tg_member, with_mention=True)
            win_db_member.month_count += 1
            win_db_member.save()
            rating.last_month_winner = win_db_member
            rating.last_month_run = datetime.now()
            rating.save()

            await self.client.send_message(chat, self.MONTH_WINNER_MESSAGE_PATTERN.format(
                rating_name=rating.name.upper(),
                member_name=member_name,
                month_name=Helper.get_month_name(datetime.now().month - 1, {'gent'}),
            ) + " 🎉")

    async def _day_roll(self, members_collection: list, rating: Rating, chat):
        if rating.last_winner \
                and rating.last_run \
                and rating.last_run >= datetime.today().replace(hour=0, minute=0, second=0, microsecond=0):
            member_name = self._get_last_winner_name(rating.last_winner, members_collection)
            await self.client.send_message(chat, self.WINNER_MESSAGE_PATTERN.format(
                rating_name=rating.name.upper(),
                member_name=member_name
            ))
        else:
            pos = random.randint(0, len(members_collection) - 1)
            tg_member, db_member = members_collection[pos]
            db_member.total_count += 1
            db_member.current_month_count += 1
            db_member.save()
            rating.last_winner = db_member
            rating.last_run = datetime.now()
            rating.save()
            await self._send_rolling_message(rating, chat)
            await self.client.send_message(chat, self.WINNER_MESSAGE_PATTERN.format(
                rating_name=rating.name.upper(),
                member_name=Helper.make_member_name(tg_member, with_mention=True)
            ))

    def _get_last_winner_name(self, winner, members_collection):
        try:
            tg_member = db_member = None
            for member in members_collection:
                tg_member, db_member = member
                if winner == db_member:
                    break
            member_name = Helper.make_member_name(tg_member)
        except DoesNotExist or AssertionError:
            member_name = self.UNKNOWN_PERSON

        return member_name

    def create_system_ratings(self, chat: Chat):
        Rating.get_or_create(
            command=self.PIDOR_KEYWORD,
            chat=chat,
            defaults={
                'name': self.PIDOR_NAME
            }
        )

        Rating.get_or_create(
            command=self.CHAD_KEYWORD,
            chat=chat,
            defaults={
                'name': self.CHAD_NAME
            }
        )

    async def _send_rolling_message(self, rating: Rating, chat):
        match rating.command:
            case self.PIDOR_KEYWORD:
                run_messages_file = Config.pidor_messages_file
            case self.CHAD_KEYWORD:
                run_messages_file = Config.chad_messages_file
            case _:
                run_messages_file = Config.custom_rating_messages_file

        try:
            with open(run_messages_file, 'r') as file:
                run_messages = []
                run_message = []

                for line in file.readlines():
                    if line == '\n':
                        if run_message:
                            run_messages.append(run_message)
                            run_message = []
                    else:
                        run_message.append(line.strip('\n '))
        except Exception as ex:
            logger.exception(ex)
            run_messages = [self.RUN_MESSAGE]

        run_msg_pos = random.randint(0, len(run_messages) - 1)
        message = await self.client.send_message(entity=chat, message='Итаааааак...')
        await sleep(self.MESSAGE_WAIT)
        text = ''

        for line in run_messages[run_msg_pos]:
            text += line + '\n'
            await message.edit(text)
            await sleep(self.MESSAGE_WAIT)
