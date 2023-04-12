# !/usr/bin/env python

import json
import random
from asyncio import sleep
from datetime import datetime

import quantumrand as qr
from peewee import fn, DoesNotExist
from telethon.tl.types import InputPeerUser, InputPeerChat, InputPeerChannel

from fsb import logger
from fsb.config import Config
from fsb.db.models import Chat, User, Member, Rating, RatingMember, RatingLeader, CacheQuantumRand
from fsb.errors import BaseFsbException, NoMembersRatingError, NoApproachableMembers
from fsb.helpers import Helper, ReturnedThread, InfoBuilder
from fsb.telegram.client import TelegramApiClient


class QuantumRandService:
    @staticmethod
    def randint(min=0, max=10):
        try:
            cache = (CacheQuantumRand.select().where(CacheQuantumRand.range == f"{min};{max}")
                     .order_by(CacheQuantumRand.created_at.asc()).first())
            value = cache.value
            cache.delete_instance()
        except DoesNotExist:
            qr.randint(min, max)


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

    WINNER_MESSAGE = "Сегодня {rating_name} дня - {member_name}!"
    MONTH_WINNER_MESSAGE = "{rating_name} {month_name} - {member_name}!"
    FEW_MONTH_WINNERS_MESSAGE = 'В {month_name} оказалось несколько лидирующих {rating_name}, ' \
                                'но придется выбрать одного.'

    LEADERSHIP_TIME = 1
    LEADERSHIP_TIME_OVER_MESSAGE = 'Одно и то же лицо не может занимать должность Лидера Чата более ' \
                                   'двух сроков подряд.\n\nПоэтому {excluded_members} ' \
                                   'автоматически {out_word}.'
    LEADERSHIP_TIME_OVER_OUT_WORD = 'выбывает'
    LEADER_ALREADY_MESSAGE = '{already_win_members} и так уже в лидерах других рейтингов в этом месяце.'

    def __init__(self, client: TelegramApiClient):
        self.client = client

    async def roll(self, rating: Rating, chat, is_month: bool = False):
        logger.info(InfoBuilder.build_log(f"{'Month' if is_month else 'Day'} rolling rating", {
            'rating': rating.id,
            'stats': self.get_month_stat(rating)
        }))

        try:
            if not rating.members.exists():
                raise NoMembersRatingError()

            # Если участник уже победил в каком-либо рейтинге в чате, то в других он участвовать не может
            actual_members = await self.client.get_dialog_members(chat)
            rating_members = rating.get_non_winners(is_month)
            members_collection = Helper.collect_members(actual_members, rating_members, Helper.COLLECT_RETURN_ONLY_DB)

            if not members_collection:
                rating_name_gent = Helper.inflect_word(rating.name, {'gent', 'plur'}).upper()
                raise NoApproachableMembers(rating_name_gent)

            if is_month:
                await self._month_roll(members_collection, rating, chat)
            else:
                await self._day_roll(members_collection, rating, chat)
        except BaseFsbException as ex:
            await self.client.send_message(chat, ex.message)

            if is_month:
                rating.last_month_run = datetime.now()
            else:
                rating.last_run = datetime.now()

            rating.save()
            return

    async def _month_roll(self, members_collection: list, rating: Rating, chat):
        if self.get_month_winner(rating):
            await self.send_last_month_winner_message(rating, chat)
        else:
            chat_members_collection = [rating_member.member for rating_member in members_collection]
            current_month = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0, day=1)
            current_month = current_month.replace(month=current_month.month - 1)

            # Участники, которые были лидерами в чате от 2 раз подряд и больше
            excluded_members_query = (RatingLeader
                                      .select()
                                      .join(RatingMember)
                                      .join(Member)
                                      .where(RatingLeader.chat == rating.chat,
                                             Member.id.in_(chat_members_collection),
                                             RatingLeader.date >= current_month.replace(month=current_month.month - self.LEADERSHIP_TIME))
                                      .group_by(Member)
                                      .having(fn.COUNT(RatingLeader.id) >= self.LEADERSHIP_TIME))
            excluded_members = [leader.rating_member.member for leader in excluded_members_query]

            # Участники, которые претендуют стать лидерами
            winners_query = (RatingMember
                             .select()
                             .where(RatingMember.id.in_(members_collection),
                                    RatingMember.member.not_in(excluded_members)))
            win_count = winners_query.select(fn.MAX(RatingMember.current_month_count)).scalar()
            winners = list(winners_query.where(RatingMember.current_month_count == win_count).execute())
            winners_len = len(winners)

            already_winner_members = list(rating.members.where(RatingMember.id.not_in(members_collection)).execute())

            for rating_member in already_winner_members:
                if rating_member.current_month_count >= win_count:
                    already_win_members = await Helper.make_members_names_string(self.client, already_winner_members, with_username=False)
                    await self.client.send_message(chat, self.LEADER_ALREADY_MESSAGE.format(
                        already_win_members=already_win_members
                    ))
                    break

            for member in excluded_members:
                rating_member = member.ratings_members.where(RatingMember.rating == rating).get()

                if rating_member.current_month_count >= win_count:
                    if len(excluded_members) > 1:
                        out_word = Helper.inflect_word(self.LEADERSHIP_TIME_OVER_OUT_WORD, {'plur'})
                    else:
                        out_word = self.LEADERSHIP_TIME_OVER_OUT_WORD
                    excluded_members_names = await Helper.make_members_names_string(self.client, excluded_members, with_username=False)
                    await self.client.send_message(chat, self.LEADERSHIP_TIME_OVER_MESSAGE.format(
                        excluded_members=excluded_members_names,
                        out_word=out_word
                    ))
                    break

            rating_name_gent = Helper.inflect_word(rating.name, {'gent', 'plur'}).upper()

            if winners_len > 1:
                await self.client.send_message(chat, self.FEW_MONTH_WINNERS_MESSAGE.format(
                        rating_name=rating_name_gent,
                        month_name=Helper.get_month_name(datetime.now().month - 1, {'loct'}),
                    ))
                win_db_member = await self._determine_winner(winners, rating, chat)
            elif winners_len == 1:
                win_db_member = winners[0]
            else:
                await self.client.send_message(chat, NoApproachableMembers(rating_name_gent).message)
                return

            win_db_member.month_count += 1
            win_db_member.save()
            rating.last_month_winner = win_db_member
            rating.last_month_run = datetime.now()
            rating.save()
            RatingLeader.create(
                rating_member=win_db_member,
                date=current_month,
                chat=win_db_member.rating.chat
            )
            RatingMember.update(current_month_count=0).where(RatingMember.rating == rating).execute()

            await self.send_last_month_winner_message(rating, chat, True)

    async def _day_roll(self, members_collection: list, rating: Rating, chat):
        if self.get_day_winner(rating):
            await self.send_last_day_winner_message(rating, chat)
        else:
            db_member = await self._determine_winner(members_collection, rating, chat)
            db_member.total_count += 1
            db_member.current_month_count += 1
            db_member.save()
            rating.last_winner = db_member
            rating.last_run = datetime.now()
            rating.save()

            await self.send_last_day_winner_message(rating, chat, True)

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

    async def _determine_winner(self, participants: list, rating: Rating, chat: Chat):
        participants_len = len(participants)

        if participants_len == 1:
            await self._send_rolling_message(rating, chat)
            return participants[0]
        elif participants_len == 0:
            return None
        else:
            qr_thread = ReturnedThread(target=qr.randint, args=(0, participants_len - 1))
            qr_thread.start()
            await self._send_rolling_message(rating, chat)
            qr_thread.join()
            pos = qr_thread.result if qr_thread.result is not None else random.randint(0, participants_len - 1)
            return participants[pos]

    async def _send_rolling_message(self, rating: Rating, chat):
        match rating.command:
            case self.PIDOR_KEYWORD:
                run_messages_file = Config.pidor_messages_file
            case self.CHAD_KEYWORD:
                run_messages_file = Config.chad_messages_file
            case _:
                run_messages_file = Config.custom_rating_messages_file

        try:
            with open(run_messages_file, 'r', encoding='utf-8') as file:
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

    async def send_last_day_winner_message(self, rating: Rating, chat, announcing: bool = False):
        tg_member = await rating.last_winner.get_telegram_member(self.client)
        await self.client.send_message(chat, self.WINNER_MESSAGE.format(
            rating_name=rating.name.upper(),
            member_name=Helper.make_member_name(tg_member, with_mention=announcing)
        ))

    async def send_last_month_winner_message(self, rating: Rating, chat, announcing: bool = False):
        tg_member = await rating.last_month_winner.get_telegram_member(self.client)
        await self.client.send_message(chat, self.MONTH_WINNER_MESSAGE.format(
            rating_name=rating.name.upper(),
            member_name=Helper.make_member_name(tg_member, with_mention=announcing),
            month_name=Helper.get_month_name(datetime.now().month - 1, {'gent'}),
        ) + (" 🎉" if announcing else ""))

    @staticmethod
    def get_day_winner(rating: Rating):
        winner = None

        if rating.last_winner \
                and rating.last_run \
                and rating.last_run >= datetime.today().replace(hour=0, minute=0, second=0, microsecond=0):
            winner = rating.last_winner

        return winner

    @staticmethod
    def get_month_winner(rating: Rating):
        winner = None

        if rating.last_month_winner \
                and rating.last_month_run \
                and rating.last_month_run >= datetime.today().replace(hour=0, minute=0, second=0, microsecond=0, day=1):
            winner = rating.last_month_winner

        return winner

    @staticmethod
    def get_month_stat(rating: Rating) -> dict:
        result = {}

        for rating_member in rating.members:
            result[rating_member.id] = rating_member.current_month_count

        return result
