# !/usr/bin/env python

from asyncio.exceptions import TimeoutError
from datetime import datetime

from dateutil.relativedelta import relativedelta as delta
from inflection import underscore
from peewee import DoesNotExist
from telethon import events
from telethon.tl.custom.button import Button

from fsb.db.models import Chat, Member, Rating, RatingMember, User
from fsb.errors import ExitControllerException, InputValueError, ConversationTimeoutError
from fsb.events.ratings import (
    RatingQueryEvent, GeneralMenuRatingEvent, RegRatingEvent, UnregRatingEvent,
    ChangeRatingEvent, DeleteRatingEvent, ListRatingEvent, MenuRatingEvent,
    DailyRollRatingEvent,
)
from fsb.handlers import ChatActionHandler, CommandHandler, MenuHandler
from fsb.helpers import Helper
from fsb.services import RatingService


class CreateRatingsOnJoinChatHandler(ChatActionHandler):
    async def run(self):
        await super().run()
        chat = Chat.get_by_telegram_id(self.chat.id)
        rating_service = RatingService(self.client)
        rating_service.create_default_ratings(chat)


class RatingsSettingsCommandHandler(CommandHandler):
    async def run(self):
        await super().run()
        try:
            ratings = Rating.select().join(RatingMember, on=(RatingMember.rating_id == Rating.id)).where(
                RatingMember.member == Member.get(
                    Member.user == User.get_by_telegram_id(self.sender.id),
                    Member.chat == Chat.get_by_telegram_id(self.chat.id)
                ),
            )
            ratings_list = [f'{rating.command} (__{rating.name}__)' for rating in ratings]
        except DoesNotExist:
            ratings_list = []
        text, buttons = GeneralMenuRatingEvent.get_message_and_buttons(self.sender.id, ratings_list)
        await self.client.send_message(self.chat, text, buttons=buttons)


class RatingCommandHandler(CommandHandler):
    PIDOR_COMMAND = RatingService.PIDOR_KEYWORD
    CHAD_COMMAND = RatingService.CHAD_KEYWORD
    ROLL_COMMAND = 'roll'
    MONTH_POSTFIX = 'month'
    YEAR_POSTFIX = 'year'
    ROLL_MONTH_COMMAND = ROLL_COMMAND + MONTH_POSTFIX
    PIDOR_MONTH_COMMAND = PIDOR_COMMAND + MONTH_POSTFIX
    CHAD_MONTH_COMMAND = CHAD_COMMAND + MONTH_POSTFIX
    ROLL_YEAR_COMMAND = ROLL_COMMAND + YEAR_POSTFIX
    PIDOR_YEAR_COMMAND = PIDOR_COMMAND + YEAR_POSTFIX
    CHAD_YEAR_COMMAND = CHAD_COMMAND + YEAR_POSTFIX

    async def run(self):
        await super().run()
        match self.command:
            case self.PIDOR_COMMAND | self.PIDOR_MONTH_COMMAND | self.PIDOR_YEAR_COMMAND:
                rating_command = self.PIDOR_COMMAND
            case self.CHAD_COMMAND | self.CHAD_MONTH_COMMAND | self.CHAD_YEAR_COMMAND:
                rating_command = self.CHAD_COMMAND
            case self.ROLL_COMMAND | self.ROLL_MONTH_COMMAND | self.ROLL_YEAR_COMMAND:
                if not self.args:
                    raise ExitControllerException
                rating_command = self.args[0]
            case _:
                raise RuntimeError

        ratings_service = RatingService(self.client)
        is_month = self.command in [self.PIDOR_MONTH_COMMAND, self.CHAD_MONTH_COMMAND, self.ROLL_MONTH_COMMAND]
        is_year = self.command in [self.PIDOR_YEAR_COMMAND, self.CHAD_YEAR_COMMAND, self.ROLL_YEAR_COMMAND]
        rating = Rating.get(
            Rating.command == rating_command,
            Rating.chat == Chat.get_by_telegram_id(self.chat.id)
        )

        if is_month:
            if ratings_service.get_month_winner(rating):
                await ratings_service.send_last_month_winner_message(rating, self.chat)
            else:
                await self.client.send_message(self.chat, "{rating_name} {month_name} еще не объявился.".format(
                    rating_name=rating.name.upper(),
                    month_name=Helper.get_month_name((datetime.now() - delta(months=1)).month, {'gent'})
                ))
        elif is_year:
            if ratings_service.get_year_winner(rating):
                await ratings_service.send_last_year_winner_message(rating, self.chat)
            else:
                await self.client.send_message(self.chat, "{rating_name} {year} года еще не объявился.".format(
                    rating_name=rating.name.upper(),
                    year=datetime.now().year
                ))
        else:
            if ratings_service.get_day_winner(rating):
                await ratings_service.send_last_day_winner_message(rating, self.chat)
            else:
                await self.client.send_message(self.chat, f"Сегодняшний {rating.name.upper()} еще не объявился.")


class StatRatingCommandHandler(CommandHandler):
    STAT_POSTFIX = 'stat'
    STAT_ALL_POSTFIX = 'all'
    PIDOR_STAT_COMMAND = RatingCommandHandler.PIDOR_COMMAND + STAT_POSTFIX
    CHAD_STAT_COMMAND = RatingCommandHandler.CHAD_COMMAND + STAT_POSTFIX
    PIDOR_STAT_ALL_COMMAND = PIDOR_STAT_COMMAND + STAT_ALL_POSTFIX
    CHAD_STAT_ALL_COMMAND = CHAD_STAT_COMMAND + STAT_ALL_POSTFIX
    STAT_COMMAND = STAT_POSTFIX
    STAT_ALL_COMMAND = STAT_COMMAND + STAT_ALL_POSTFIX

    async def run(self):
        await super().run()
        match self.command:
            case self.PIDOR_STAT_COMMAND | self.PIDOR_STAT_ALL_COMMAND:
                rating_command = RatingService.PIDOR_KEYWORD
            case self.CHAD_STAT_COMMAND | self.CHAD_STAT_ALL_COMMAND:
                rating_command = RatingService.CHAD_KEYWORD
            case self.STAT_COMMAND | self.STAT_ALL_COMMAND:
                if not self.args:
                    raise ExitControllerException
                rating_command = self.args[0]
            case _:
                raise RuntimeError

        is_all = self.command in [self.PIDOR_STAT_ALL_COMMAND, self.CHAD_STAT_ALL_COMMAND, self.STAT_ALL_COMMAND]
        rating = Rating.get(
            Rating.command == rating_command,
            Rating.chat == Chat.get_by_telegram_id(self.chat.id)
        )
        message = await RatingService(self.client).get_stat_message(rating, is_all)

        await self.client.send_message(self.chat, message)


class RatingsSettingsQueryHandler(MenuHandler):
    async def run(self):
        await super().run()
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
                    Member.user == User.get_by_telegram_id(self.sender.id),
                    Member.chat == Chat.get_by_telegram_id(self.chat.id)
                ),
            ).order_by(Rating.id)
            ratings_list = [f'{rating.command} (__{rating.name}__)' for rating in ratings]
        except DoesNotExist:
            ratings_list = []
        text, buttons = GeneralMenuRatingEvent.get_message_and_buttons(self.sender.id, ratings_list)
        await self.menu_message.edit(text, buttons=buttons)

    async def action_reg_menu(self):
        chat = Chat.get_by_telegram_id(self.chat.id)
        member = Member.get(
            Member.user == User.get_by_telegram_id(self.sender.id),
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
                f"{rating.command}",
                RegRatingEvent(sender_id=self.sender.id, rating_id=rating.id, member_id=member.id).save_get_id()
            ))
        buttons = Helper.make_buttons_layout(buttons, (
            "<< К меню рейтингов",
            GeneralMenuRatingEvent(self.sender.id).save_get_id()
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
            await self.action_reg_menu()

    async def action_unreg_menu(self):
        chat = Chat.get_by_telegram_id(self.chat.id)
        member = Member.get(
            Member.user == User.get_by_telegram_id(self.sender.id),
            Member.chat == chat
        )
        ratings = Rating.select().join(RatingMember, on=(RatingMember.rating_id == Rating.id)).where(
            Rating.chat == chat,
            RatingMember.member == member
        )

        buttons = []
        for rating in ratings:
            buttons.append((
                f"{rating.command}",
                UnregRatingEvent(sender_id=self.sender.id, rating_id=rating.id, member_id=member.id).save_get_id()
            ))
        buttons = Helper.make_buttons_layout(buttons, (
            "<< К меню рейтингов",
            GeneralMenuRatingEvent(self.sender.id).save_get_id()
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
            await self.action_unreg_menu()
        else:
            await self.client.send_message(self.chat, "Ты уже разреган")
            return

    async def action_list(self, new_message: bool=False):
        chat = Chat.get_by_telegram_id(self.chat.id)
        ratings = Rating.select().where(Rating.chat == chat).order_by(Rating.id)
        buttons = []

        for rating in ratings:
            buttons.append((
                rating.command,
                MenuRatingEvent(sender_id=self.sender.id, rating_id=rating.id).save_get_id()
            ))

        buttons = Helper.make_buttons_layout(
            buttons,
            ("<< К меню рейтингов", GeneralMenuRatingEvent(self.sender.id).save_get_id())
        )
        text = "Список рейтингов:"

        if new_message:
            await self.client.send_message(self.chat, text, buttons=buttons)
        else:
            await self.menu_message.edit(text, buttons=buttons)

    async def get_rating_params(self, conv):
        response = conv.wait_event(
            events.NewMessage(forwards=False, chats=self.chat, from_users=self.sender.id),
            timeout=self.INPUT_TIMEOUT
        )
        await conv.send_message('Введи команду и название для рейтинга через запятую\n(Command, name)')
        response_event_name = await response

        command, name = Rating.parse_from_message(response_event_name.message.text)
        chat = Chat.get_by_telegram_id(self.chat.id)

        if Rating.get_or_none(Rating.chat == chat, Rating.command == command):
            return None
        else:
            return name, command, chat

    async def action_create(self):
        async with self.client._client.conversation(self.chat) as conv:
            try:
                params = await self.get_rating_params(conv)

                if params:
                    rating_id = Rating.create(name=params[0], command=params[1], chat=params[2]).save_get_id()
                    await conv.send_message(f"Создан рейтинг: {params[0]} (__{params[1]}__)")
                else:
                    await conv.send_message("Такой рейтинг уже существует")
                    return

                self.query_event.rating_id = rating_id
                await self.action_menu()
            except TimeoutError:
                await conv.send_message(ConversationTimeoutError.message)
            except InputValueError as ex:
                await conv.send_message(ex.message)

    async def action_change(self):
        rating = self.query_event.get_rating()

        async with self.client._client.conversation(self.chat) as conv:
            try:
                params = await self.get_rating_params(conv)

                if params:
                    old_name = rating.name
                    old_command = rating.command
                    rating.name = params[0]
                    rating.command = params[1]
                    rating.save()
                    await conv.send_message(
                        f"Изменен рейтинг с {old_command} (__{old_name}__) на {rating.command} (__{rating.name}__)"
                    )
                else:
                    await conv.send_message("Такой рейтинг уже существует")
                    return
            except TimeoutError:
                await conv.send_message(ConversationTimeoutError.message)
            except InputValueError as ex:
                await conv.send_message(ex.message)

    async def action_delete(self):
        rating = self.query_event.get_rating()
        rating.delete_instance()
        await self.client.send_message(self.chat, f"Удалена роль: {rating.command} (__{rating.name}__)")
        await self.action_list()

    async def action_menu(self, new_message: bool = False):
        rating = self.query_event.get_rating()
        members = Helper.collect_members(
            await self.client.get_dialog_members(self.chat),
            RatingMember.select().where(RatingMember.rating == rating)
        )
        members_names = []

        for tg_member, db_member in members:
            members_names.append(Helper.make_member_name(tg_member))

        text = f"Меню рейтинга **{rating.command}** ({rating.name})\n\n**Участники:**\n" \
            + '\n'.join(members_names)
        back_button = Button.inline('<< К списку ролей', ListRatingEvent(self.sender.id).save_get_id())
        autorun_button = Button.inline(
            f'Авторолл: {"ВКЛ" if rating.autorun else "ВЫКЛ"}',
            DailyRollRatingEvent(self.sender.id, rating.id).save_get_id()
        )

        if rating.command in [RatingService.PIDOR_KEYWORD, RatingService.CHAD_KEYWORD]:
            buttons = [
                [autorun_button],
                [back_button],
            ]
        else:
            buttons = [
                [
                    Button.inline('Изменить', ChangeRatingEvent(self.sender.id, rating.id).save_get_id()),
                    Button.inline('Удалить', DeleteRatingEvent(self.sender.id, rating.id).save_get_id()),
                    autorun_button,
                ],
                [back_button],
            ]

        if new_message:
            await self.client.send_message(self.chat, text, buttons=buttons)
        else:
            await self.menu_message.edit(text, buttons=buttons)

    async def action_daily_roll(self):
        rating = self.query_event.get_rating()
        rating.autorun = not rating.autorun
        rating.save()
        await self.action_menu()
