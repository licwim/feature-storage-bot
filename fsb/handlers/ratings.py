# !/usr/bin/env python

from datetime import datetime

from inflection import underscore
from peewee import DoesNotExist
from telethon import events
from telethon.tl.custom.button import Button

from fsb.db.models import Chat, Member, Rating, RatingMember, User
from fsb.error import ExitControllerException, InputValueError
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
        rating_service.create_system_ratings(chat)


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
    ROLL_MONTH_COMMAND = ROLL_COMMAND + MONTH_POSTFIX
    PIDOR_MONTH_COMMAND = PIDOR_COMMAND + MONTH_POSTFIX
    CHAD_MONTH_COMMAND = CHAD_COMMAND + MONTH_POSTFIX

    async def run(self):
        await super().run()
        match self.command:
            case self.PIDOR_COMMAND | self.PIDOR_MONTH_COMMAND:
                rating_command = self.PIDOR_COMMAND
            case self.CHAD_COMMAND | self.CHAD_MONTH_COMMAND:
                rating_command = self.CHAD_COMMAND
            case self.ROLL_COMMAND | self.ROLL_MONTH_COMMAND:
                if not self.args:
                    raise ExitControllerException
                rating_command = self.args[0]
            case _:
                raise RuntimeError

        ratings_service = RatingService(self.client)
        is_month = self.command in [self.PIDOR_MONTH_COMMAND, self.CHAD_MONTH_COMMAND, self.ROLL_MONTH_COMMAND]
        rating = Rating.get(
            Rating.command == rating_command,
            Rating.chat == Chat.get_by_telegram_id(self.chat.id)
        )

        if is_month \
                and (not rating.last_month_winner \
                or not rating.last_month_run \
                or rating.last_month_run < datetime.today().replace(hour=0, minute=0, second=0, microsecond=0, day=1)):
            await self.client.send_message(self.chat, f"{rating.name.upper()} этого месяца еще не объявился.")
        else:
            await ratings_service.roll(rating, self.chat, is_month)


class StatRatingCommandHandler(CommandHandler):
    STAT_POSTFIX = 'stat'
    PIDOR_STAT_COMMAND = RatingCommandHandler.PIDOR_COMMAND + STAT_POSTFIX
    CHAD_STAT_COMMAND = RatingCommandHandler.CHAD_COMMAND + STAT_POSTFIX
    PIDOR_MONTH_STAT_COMMAND = PIDOR_STAT_COMMAND + RatingCommandHandler.MONTH_POSTFIX
    CHAD_MONTH_STAT_COMMAND = CHAD_STAT_COMMAND + RatingCommandHandler.MONTH_POSTFIX
    STAT_COMMAND = STAT_POSTFIX
    STAT_MONTH_COMMAND = STAT_COMMAND + RatingCommandHandler.MONTH_POSTFIX

    async def run(self):
        await super().run()
        match self.command:
            case self.PIDOR_STAT_COMMAND | self.PIDOR_MONTH_STAT_COMMAND:
                rating_command = RatingService.PIDOR_KEYWORD
            case self.CHAD_STAT_COMMAND | self.CHAD_MONTH_STAT_COMMAND:
                rating_command = RatingService.CHAD_KEYWORD
            case self.STAT_COMMAND | self.STAT_MONTH_COMMAND:
                if not self.args:
                    raise ExitControllerException
                rating_command = self.args[0]
            case _:
                raise RuntimeError

        is_month = self.command in [self.PIDOR_MONTH_STAT_COMMAND, self.CHAD_MONTH_STAT_COMMAND, self.STAT_MONTH_COMMAND]
        rating = Rating.get(
            Rating.command == rating_command,
            Rating.chat == Chat.get_by_telegram_id(self.chat.id)
        )

        order = RatingMember.month_count.desc() if is_month else RatingMember.count.desc()
        actual_members = await self.client.get_dialog_members(self.chat)
        rating_members = RatingMember.select().where(RatingMember.rating == rating).order_by(order)
        members_collection = Helper.collect_members(actual_members, rating_members)
        if not members_collection:
            return

        message = f"**Результаты {rating.name.upper()} следующего месяца:**\n" if is_month \
            else f"**Результаты {rating.name.upper()} дня (месяца):**\n"
        pos = 1

        for member in members_collection:
            tg_member, db_member = member
            count_msg = f"{Helper.make_count_str(db_member.current_month_count)}\n" if is_month \
                     else f"{Helper.make_count_str(db_member.count, db_member.month_count)}\n"
            message += f"#**{pos}**   {Helper.make_member_name(tg_member)} - {count_msg}"
            pos += 1
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
