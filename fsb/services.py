# !/usr/bin/env python

import json
import logging
import random
from asyncio import sleep
from datetime import datetime

import quantumrand as qr
from dateutil.relativedelta import relativedelta as delta
from peewee import fn
from telethon.tl.functions.messages import GetStickerSetRequest
from telethon.tl.types import InputPeerUser, InputPeerChat, InputPeerChannel
from telethon.tl.types import InputStickerSetShortName

from fsb.config import config
from fsb.db.models import Chat, User, Member, Rating, RatingMember, RatingLeader, CacheQuantumRand, Modules
from fsb.errors import BaseFsbException, NoMembersRatingError, NoApproachableMembers
from fsb.helpers import Helper, ReturnedThread, InfoBuilder
from fsb.telegram.client import TelegramApiClient


class QuantumRandService:
    @staticmethod
    def randint(min=0, max=10):
        return qr.randint(min, max, QuantumRandService.generator())

    @staticmethod
    def generator(data_type='uint16', cache_size=1024):
        logger = logging.getLogger('main')

        while True:
            if not CacheQuantumRand.select().where(CacheQuantumRand.type == data_type).first():
                data = qr.get_data(data_type, cache_size, cache_size)
                CacheQuantumRand.insert_many(
                    [(data_item, data_type) for data_item in data],
                    [CacheQuantumRand.value, CacheQuantumRand.type]
                ).execute()

            for cache in CacheQuantumRand.select().where(CacheQuantumRand.type == data_type):
                value = cache.value
                cache.delete_instance()
                logger.info(f'QuantumRandService generator value: {value}')
                yield value


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
            chat.real_dirty = True
            chat.name = name
            chat.type = type
            chat.input_peer = input_chat
            if chat.is_dirty():
                chat.save(only=chat.dirty_fields)
            chat.real_dirty = False

        await self.create_members(entity=entity, chat=chat, update=update)

        self.create_modules(chat)

        return chat

    async def create_members(self, event=None, entity=None, chat=None, update: bool = False):
        if event:
            entity = event.chat
        elif not entity:
            return None

        if not chat:
            chat = Chat.get_by_telegram_id(entity.id)

        for tg_member in await self.client.get_dialog_members(entity):
            user = self.create_user(entity=tg_member, update=update)
            Member.get_or_create(chat=chat, user=user)

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
            user.real_dirty = True
            user.name = name
            user.nickname = entity.username
            user.phone = entity.phone
            user.input_peer = input_chat
            if user.is_dirty():
                user.save(only=user.dirty_fields)
            user.real_dirty = False

        return user

    def create_modules(self, chat: Chat):
        modules = Modules.get_or_create(chat=chat)[0]

        return modules

    async def init_chats(self):
        for chat in Chat.select():
            entity = await self.client.get_entity(chat.telegram_id)
            await self.create_chat(entity=entity, update=True)


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

    OUT_MESSAGE = '{excluded_members} автоматически {out_word} из гонки за звание ' \
                  '{rating_name_gent_sing} месяца, '
    OUT_WORD = 'выбывает'
    LEADER_ALREADY_MESSAGE = OUT_MESSAGE + 'поскольку и так уже в лидерах других рейтингов в этом месяце.'
    YEAR_WINNER_MESSAGE = "В прошедшем {year} году самым большим {rating_name_ablt_sing} был {member_name}!"
    FEW_YEAR_WINNERS_MESSAGE = 'В {year} году оказалось несколько лидирующих {rating_name_gent_plur}, ' \
                               'но остаться должен только один.'

    def __init__(self, client: TelegramApiClient):
        self.client = client
        self.logger = logging.getLogger('main')

    async def roll(self, rating: Rating, chat, is_month: bool = False):
        self.logger.info(InfoBuilder.build_log(f"{'Month' if is_month else 'Day'} rolling rating", {
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
                raise NoApproachableMembers(rating.name)

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
            current_month = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0, day=1) - delta(months=1)

            # Участники, которые претендуют стать лидерами
            winners_query = (RatingMember
                             .select()
                             .where(RatingMember.id.in_(members_collection)))
            win_count = winners_query.select(fn.MAX(RatingMember.current_month_count)).scalar()
            winners = list(winners_query.where(RatingMember.current_month_count == win_count).execute())
            winners_len = len(winners)

            already_winner_members = list(rating.members.where(RatingMember.id.not_in(members_collection)).execute())

            rating_name_gent_sing = Helper.inflect_word(rating.name, {'gent', 'sing'}).upper()
            rating_name_gent_plur = Helper.inflect_word(rating.name, {'gent', 'plur'}).upper()

            for rating_member in already_winner_members:
                if win_count is not None and rating_member.current_month_count >= win_count:
                    if len(already_winner_members) > 1:
                        out_word = Helper.inflect_word(self.OUT_WORD, {'plur'})
                    else:
                        out_word = self.OUT_WORD

                    already_winner_members_names = await Helper.make_members_names_string(self.client,
                                                                                          already_winner_members,
                                                                                          with_username=False)
                    await self.client.send_message(chat, self.LEADER_ALREADY_MESSAGE.format(
                        excluded_members=already_winner_members_names,
                        out_word=out_word,
                        rating_name_gent_sing=rating_name_gent_sing
                    ))
                    break

            if winners_len > 1:
                await self.client.send_message(chat, self.FEW_MONTH_WINNERS_MESSAGE.format(
                    rating_name=rating_name_gent_plur,
                    month_name=Helper.get_month_name((datetime.now() - delta(months=1)).month, {'loct'}),
                ))
                win_db_member = await self._determine_winner(winners, rating, chat)
            elif winners_len == 1:
                win_db_member = winners[0]
            else:
                await self.client.send_message(chat, NoApproachableMembers(rating.name).message)
                return

            win_db_member.month_count += 1
            win_db_member.current_year_count += 1
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

    def create_default_ratings(self, chat: Chat):
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
            qr_thread = ReturnedThread(target=QuantumRandService.randint, args=(0, participants_len - 1))
            qr_thread.start()
            await self._send_rolling_message(rating, chat)
            qr_thread.join()
            assert qr_thread.result is not None
            return participants[qr_thread.result]

    async def _send_rolling_message(self, rating: Rating, chat):
        match rating.command:
            case self.PIDOR_KEYWORD:
                run_messages_file = config.content.pidor_messages_file
            case self.CHAD_KEYWORD:
                run_messages_file = config.content.chad_messages_file
            case _:
                run_messages_file = config.content.custom_rating_messages_file

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

                if run_message:
                    run_messages.append(run_message)
        except Exception as ex:
            self.logger.exception(ex)
            run_messages = [self.RUN_MESSAGE]

        message = await self.client.send_message(entity=chat, message='Итаааааак...')
        await sleep(self.MESSAGE_WAIT)
        text = ''

        for line in random.choice(run_messages):
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
            month_name=Helper.get_month_name((datetime.now() - delta(months=1)).month, {'gent'}),
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

    @staticmethod
    def get_year_winner(rating: Rating):
        winner = None

        if rating.last_year_winner \
                and rating.last_year_run \
                and rating.last_year_run >= datetime.today().replace(hour=0, minute=0, second=0, microsecond=0, day=1,
                                                                     month=1):
            winner = rating.last_month_winner

        return winner

    @staticmethod
    def get_year_stat(rating: Rating) -> dict:
        result = {}

        for rating_member in rating.members:
            result[rating_member.id] = rating_member.month_count

        return result

    async def send_last_year_winner_message(self, rating: Rating, chat, announcing: bool = False):
        tg_member = await rating.last_year_winner.get_telegram_member(self.client)
        rating_name_lexeme = Helper.get_words_lexeme(rating_name=rating.name.upper())
        year = (datetime.now().replace(hour=0, minute=10, second=0, microsecond=0, day=1, month=1)
                - delta(years=1)).year
        winner_message = self.YEAR_WINNER_MESSAGE.format(
            member_name=Helper.make_member_name(tg_member, with_mention=announcing),
            year=year,
            **rating_name_lexeme,
        )

        if announcing:
            with open(config.content.rating_congratulations_file, 'r', encoding='utf-8') as file:
                congratulations = file.readlines()
                congratulation = random.choice(congratulations).strip(' \n')
                congratulation = congratulation.format(**rating_name_lexeme)
            with open(config.content.year_emojis_file, 'r', encoding='utf-8') as file:
                emojis = file.readlines()
                emoji = random.choice(emojis).strip(' \n')

            await self.client.send_message(chat, winner_message + ' ' + congratulation)
            await self.client.send_message(chat, emoji)
        else:
            await self.client.send_message(chat, winner_message)

    async def roll_year(self, rating: Rating, chat):
        self.logger.info(InfoBuilder.build_log(f"Year rolling rating", {
            'rating': rating.id,
            'stats': self.get_year_stat(rating)
        }))

        try:
            if not rating.members.exists():
                raise NoMembersRatingError()

            actual_members = await self.client.get_dialog_members(chat)
            rating_members = rating.members
            members_collection = Helper.collect_members(actual_members, rating_members, Helper.COLLECT_RETURN_ONLY_DB)
            year = (datetime.now().replace(hour=0, minute=10, second=0, microsecond=0, day=1, month=1)
                    - delta(years=1)).year

            if not members_collection:
                raise NoApproachableMembers(rating.name)

            winners_query = (RatingMember
                             .select()
                             .where(RatingMember.id.in_(members_collection)))
            win_count = winners_query.select(fn.MAX(RatingMember.current_year_count)).scalar()
            winners = list(winners_query.where(RatingMember.current_year_count == win_count).execute())
            winners_len = len(winners)

            if winners_len > 1:
                await self.client.send_message(chat, self.FEW_YEAR_WINNERS_MESSAGE.format(
                    year=year,
                    **Helper.get_words_lexeme(rating_name=rating.name.upper())
                ))
                win_db_member = await self._determine_winner(winners, rating, chat)
            elif winners_len == 1:
                win_db_member = winners[0]
            else:
                await self.client.send_message(chat, NoApproachableMembers(rating.name).message)
                return

            rating.last_year_winner = win_db_member
            rating.last_year_run = datetime.now()
            rating.save()
            RatingMember.update(current_year_count=0).where(RatingMember.rating == rating).execute()

            await self.send_last_year_winner_message(rating, chat, True)
        except BaseFsbException as ex:
            await self.client.send_message(chat, ex.message)

    async def fool_roll(self, rating: Rating, chat, is_month: bool = False):
        if is_month:
            actual_members = await self.client.get_dialog_members(chat)
            member_for_fullname = random.choice(actual_members)
            actual_members_with_username = [
                member for member in actual_members if member.username and member != member_for_fullname
            ]
            member_for_username = random.choice(actual_members_with_username)
            member_name = (Helper.make_member_name(member_for_fullname, with_username=False, with_mention=False)
                           + f' ([@{member_for_username.username}](https://rb.gy/qljtn1))')
            await self.client.send_message(chat, self.MONTH_WINNER_MESSAGE.format(
                rating_name=rating.name.upper(),
                member_name=member_name,
                month_name=Helper.get_month_name((datetime.now() - delta(months=1)).month, {'gent'}),
            ) + " 🎉", link_preview=False)
        else:
            await self._send_rolling_message(rating, chat)
            await FoolService(self.client).send_message(chat)

    async def get_stat_message(self, rating: Rating, is_all: bool):
        order = RatingMember.total_count.desc() if is_all else RatingMember.current_month_count.desc()
        actual_members = await self.client.get_dialog_members(rating.chat.telegram_id)
        rating_members = RatingMember.select().where(RatingMember.rating == rating).order_by(order)
        members_collection = Helper.collect_members(actual_members, rating_members)

        if not members_collection:
            return None

        rating_name = Helper.inflect_word(rating.name, {'gent', 'plur'})
        message = f"**Статистика {rating_name.upper()} __(дни / месяцы)__:**\n" if is_all \
            else f"**Статистика {rating_name.upper()} этого месяца:**\n"
        pos = 1

        for member in members_collection:
            tg_member, db_member = member
            count_msg = f"{Helper.make_count_str(db_member.total_count, db_member.month_count)}\n" if is_all \
                else f"{Helper.make_count_str(db_member.current_month_count)}\n"
            message += f"#**{pos}**   {Helper.make_member_name(tg_member)} - {count_msg}"
            pos += 1

        return message


class FoolService:
    def __init__(self, client: TelegramApiClient):
        self.client = client
        self.logger = logging.getLogger('main')

    async def send_message(self, chat):
        message = 'Nope'
        is_file = False
        sticker_set_name = config.fool.sticker_set_name
        sticker_id = config.fool.sticker_set_documents_id

        if sticker_set_name and sticker_id:
            sticker_set = await self.client.request(GetStickerSetRequest(InputStickerSetShortName(sticker_set_name)))
            stickers = [sticker for sticker in sticker_set.documents if sticker.id == sticker_id]

            if stickers:
                message = stickers[0]
                is_file = True

        await self.client.send_message(chat, message, is_file=is_file)


class BirthdayService:
    BIRTHDAY_MESSAGE = 'С Днём Рождения, {name}! 🎈'

    def __init__(self, client: TelegramApiClient):
        self.client = client
        self.logger = logging.getLogger('main')

    async def send_message(self, chat: Chat):
        for user in chat.users.where(fn.DATE_FORMAT(User.birthday, '%m-%d') == datetime.today().strftime('%m-%d')):
            await self.client.send_message(chat.telegram_id, self.BIRTHDAY_MESSAGE.format(
                name=Helper.make_member_name(await user.get_telegram_member(self.client), with_mention=True)
            ))
