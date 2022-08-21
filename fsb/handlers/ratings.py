# !/usr/bin/env python

import random
from asyncio import sleep
from datetime import datetime

from inflection import underscore
from peewee import DoesNotExist

from events.ratings import RatingQueryEvent, GeneralMenuRatingEvent, RegRatingEvent, UnregRatingEvent
from fsb.db.models import Chat, Member, Rating, RatingMember, User
from fsb.handlers import ChatActionHandler, CommandHandler, MenuHandler
from fsb.helpers import Helper

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


class CreateRatingsOnJoinChatHandler(ChatActionHandler):
    async def run(self):
        chat = Chat.get(telegram_id=self.chat.id)

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


class RatingsSettingsCommandHandler(CommandHandler):
    async def run(self):
        try:
            ratings = Rating.select().join(RatingMember, on=(RatingMember.rating_id == Rating.id)).where(
                RatingMember.member == Member.get(
                    Member.user == User.get(User.telegram_id == self.event.message.sender.id),
                    Member.chat == Chat.get(Chat.telegram_id == self.chat.id)
                ),
            )
            ratings_list = [rating.name for rating in ratings]
        except DoesNotExist:
            ratings_list = []
        text, buttons = GeneralMenuRatingEvent.get_message_and_buttons(self.message.sender.id, ratings_list)
        await self.client.send_message(self.chat, text, buttons=buttons)


class RatingCommandHandler(CommandHandler):
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

    async def run(self):
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
            chat=Chat.get(Chat.telegram_id == self.chat.id),
            defaults={
                'command': rating_name
            }
        )[0]

        actual_members = await self.client.get_dialog_members(self.chat)
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
                member_name = Helper.make_member_name(tg_member, with_mention=True)
            except DoesNotExist or AssertionError:
                member_name = "__какой-то неизвестный хер__"
            await self.client.send_message(self.chat, self.WINNER_MESSAGE_PATTERN.format(
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
            message = await self.client._client.send_message(entity=self.chat, message='Итаааааак...')
            await sleep(self.MESSAGE_WAIT)
            text = ''
            for line in run_messages:
                text += line + '\n'
                await message.edit(text)
                await sleep(self.MESSAGE_WAIT)
            await self.client.send_message(self.chat, self.WINNER_MESSAGE_PATTERN.format(
                msg_name=msg_name,
                member_name=Helper.make_member_name(tg_member, with_mention=True)
            ))


class StatRatingCommandHandler(CommandHandler):
    PIDOR_STAT_COMMAND = RatingCommandHandler.PIDOR_COMMAND + 'stat'
    CHAD_STAT_COMMAND = RatingCommandHandler.CHAD_COMMAND + 'stat'

    async def run(self):
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
            chat=Chat.get(Chat.telegram_id == self.chat.id),
            defaults={
                'command': rating_name
            }
        )[0]

        actual_members = await self.client.get_dialog_members(self.chat)
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
        await self.client.send_message(self.chat, message)


class RatingsSettingsQueryHandler(MenuHandler):
    async def run(self):
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
                    Member.user == User.get(User.telegram_id == self.sender),
                    Member.chat == Chat.get(Chat.telegram_id == self.chat.id)
                ),
            )
            ratings_list = [rating.name for rating in ratings]
        except DoesNotExist:
            ratings_list = []
        text, buttons = GeneralMenuRatingEvent.get_message_and_buttons(self.sender, ratings_list)
        await self.menu_message.edit(text, buttons=buttons)

    async def action_reg_menu(self):
        chat = Chat.get(Chat.telegram_id == self.chat.id)
        member = Member.get(
            Member.user == User.get(User.telegram_id == self.sender),
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
                RegRatingEvent(sender=self.sender, rating_id=rating.id, member_id=member.id).save_get_id()
            ))
        buttons = Helper.make_buttons_layout(buttons, (
            "<< К меню рейтингов",
            GeneralMenuRatingEvent(self.sender).save_get_id()
        ))

        await self.menu_message.edit("Куда регаться", buttons=buttons)

    async def action_reg(self):
        rating = self.query_event.get_rating()
        member = self.query_event.get_member()
        rating_member = RatingMember.get_or_none(
            RatingMember.rating == rating,
            RatingMember.member == member
        )
        if rating_member:
            await self.client.send_message(self.chat, "Ты уже зареган")
            return
        else:
            RatingMember.create(rating=rating, member=member)
            tg_member = await self.client.get_entity(member.user.telegram_id)
            await self.client.send_message(
                self.chat,
                f"{tg_member.first_name} теперь зареган в {rating.name}"
            )

    async def action_unreg_menu(self):
        chat = Chat.get(Chat.telegram_id == self.chat.id)
        member = Member.get(
            Member.user == User.get(User.telegram_id == self.sender),
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
                UnregRatingEvent(sender=self.sender, rating_id=rating.id, member_id=member.id).save_get_id()
            ))
        buttons = Helper.make_buttons_layout(buttons, (
            "<< К меню рейтингов",
            GeneralMenuRatingEvent(self.sender).save_get_id()
        ))

        await self.menu_message.edit("Откуда разрегаться", buttons=buttons)

    async def action_unreg(self):
        rating = self.query_event.get_rating()
        member = self.query_event.get_member()
        rating_member = RatingMember.get_or_none(
            RatingMember.rating == rating,
            RatingMember.member == member
        )
        if rating_member:
            rating_member.delete_instance()
            tg_member = await self.client.get_entity(member.user.telegram_id)
            await self.client.send_message(
                self.chat,
                f"{tg_member.first_name} теперь разреган из {rating.name}"
            )
        else:
            await self.client.send_message(self.chat, "Ты уже разреган")
            return
