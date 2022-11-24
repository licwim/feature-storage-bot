# !/usr/bin/env python

import json
import random
from asyncio import sleep
from datetime import datetime

from peewee import DoesNotExist
from telethon.tl.types import InputPeerUser, InputPeerChat, InputPeerChannel

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

    PIDOR_RUN_MESSAGES = [
        [
            '«Великан сидит в пещере», —',
            'Говорят в лесу все звери.',
            'Великан голодный ищет,',
            'Кто ему сгодится в пищу,',
            'Звери спрятались в кусты —',
            'Значит, геем будешь ты!',
        ],
        [
            'Вышел месяц из тумана,',
            'Вынул ножик из кармана.',
            'Буду резать, буду бить,',
            'Всё равно ты пидор!',
        ],
        [
            'Шёл котик по лавочке,',
            'Раздавал булавочки.',
            'Шёл по скамеечке —',
            'Раздавал копеечки:',
            'Кому десять, кому пять —',
            'Выходи, ПИДОР!',
        ],
        [
            'Высоко‑превысоко',
            'Кинул я свой мяч легко.',
            'Но упал мой мяч с небес,',
            'Закатился в тёмный лес.',
            'Раз, два, три, четыре, пять,',
            'Пидора иду искать.',

        ],
        [
            'На печи калачи,',
            'Как огонь, горячи.',
            'Пришёл мальчик,',
            'Обжёг пальчик.',
            'Пошёл на базар,',
            'Пидором стал.',
        ],
        [
            'Вдаль бежит река лесная,',
            'Вдоль неё растут кусты.',
            'Всех в игру я приглашаю,',
            'Мы играем — пидор ты!',
        ]
    ]

    CHAD_RUN_MESSAGES = [
        [
            'Сидел король на лавочке,',
            'Считал свои булавочки:',
            '«Раз, два, три»',
            'Королевой будешь ты!',

        ],
    ]

    CUSTOM_RUN_MESSAGES = [
        [
            'На окне стоит бутылка,',
            'А в бутылке лимонад.',
            'Кто скорей возьмёт бутылку,',
            'Тот победе будет рад.',
        ],
    ]

    WINNER_MESSAGE_PATTERN = "Сегодня {msg_name} дня - {member_name}!"
    MONTH_WINNER_MESSAGE_PATTERN = "{msg_name} этого месяца - {member_name}!"
    UNKNOWN_PERSON = "__какой-то неизвестный хер__"

    def __init__(self, client: TelegramApiClient):
        self.client = client

    async def roll(self, rating: Rating, chat, is_month: bool = False):
        match rating.command:
            case self.PIDOR_KEYWORD:
                run_messages = self.PIDOR_RUN_MESSAGES
            case self.CHAD_KEYWORD:
                run_messages = self.CHAD_RUN_MESSAGES
            case _:
                run_messages = self.CUSTOM_RUN_MESSAGES

        actual_members = await self.client.get_dialog_members(chat)
        rating_members = RatingMember.select().where(RatingMember.rating == rating)
        members_collection = Helper.collect_members(actual_members, rating_members)
        if not members_collection:
            return

        if is_month:
            if rating.last_month_winner \
                    and rating.last_month_run \
                    and rating.last_month_run >= datetime.today().replace(hour=0, minute=0, second=0, microsecond=0, day=1):
                member_name = self._get_last_winner_name(rating.last_month_winner, members_collection)
                await self.client.send_message(chat, self.MONTH_WINNER_MESSAGE_PATTERN.format(
                    msg_name=rating.name.upper(),
                    member_name=member_name
                ))
            else:
                win_tg_member, win_db_member = members_collection[0]

                for tg_member, db_member in members_collection:
                    db_member.current_month_count = 0
                    db_member.save()

                member_name = Helper.make_member_name(win_tg_member, with_mention=True)
                win_db_member.month_count += 1
                win_db_member.save()
                rating.last_month_winner = win_db_member
                rating.last_month_run = datetime.now()
                rating.save()

                await self.client.send_message(rating.chat.telegram_id, self.MONTH_WINNER_MESSAGE_PATTERN.format(
                                             msg_name=rating.name.upper(),
                                             member_name=member_name
                                         ) + "\nПоздравляем! 🎉")
        else:
            if rating.last_winner \
                    and rating.last_run \
                    and rating.last_run >= datetime.today().replace(hour=0, minute=0, second=0, microsecond=0):
                member_name = self._get_last_winner_name(rating.last_winner, members_collection)
                await self.client.send_message(chat, self.WINNER_MESSAGE_PATTERN.format(
                    msg_name=rating.name.upper(),
                    member_name=member_name
                ))
            else:
                pos = random.randint(0, len(members_collection) - 1)
                run_msg_pos = random.randint(0, len(run_messages) - 1)
                tg_member, db_member = members_collection[pos]
                db_member.count += 1
                db_member.current_month_count += 1
                db_member.save()
                rating.last_winner = db_member
                rating.last_run = datetime.now()
                rating.save()
                message = await self.client.send_message(entity=chat, message='Итаааааак...')
                await sleep(self.MESSAGE_WAIT)
                text = ''
                for line in run_messages[run_msg_pos]:
                    text += line + '\n'
                    await message.edit(text)
                    await sleep(self.MESSAGE_WAIT)
                await self.client.send_message(chat, self.WINNER_MESSAGE_PATTERN.format(
                    msg_name=rating.name.upper(),
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
