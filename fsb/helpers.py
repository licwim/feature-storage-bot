# !/usr/bin/env python

import json
import logging
from datetime import datetime
from threading import Thread
from typing import Union, Iterable

import yaml
from pymorphy3 import MorphAnalyzer
from telethon.tl.custom.button import Button
from telethon.tl.patched import Message

from fsb.config import config
from fsb.events.common import CallbackQueryEventDTO, EventDTO, MessageEventDTO, ChatActionEventDTO


class InfoBuilder:

    JSON = 1
    YAML = 2

    @staticmethod
    def builder_decorator(callback: callable):
        def build(*args, **kwargs):
            data_info = callback(*args, **kwargs)
            view_type = kwargs.get('view_type')
            view_type = view_type if isinstance(view_type, int) else InfoBuilder.JSON
            match view_type:
                case InfoBuilder.JSON:
                    return json.dumps(data_info, sort_keys=False, indent=2, ensure_ascii=False)
                case InfoBuilder.YAML:
                    return yaml.dump(data_info, sort_keys=False, default_flow_style=False, allow_unicode=True)
        return build

    @staticmethod
    @builder_decorator
    def build_log(message: str, data):
        data_info = {
            'message': message,
            'data': data,
        }
        return data_info

    @staticmethod
    @builder_decorator
    def build_message_info_by_message_event(event: MessageEventDTO, view_type: int = None):
        assert isinstance(event, MessageEventDTO)
        chat_info = InfoBuilder.build_chat_info(event)

        data_info = {
            'chat': chat_info,
            'message': event.message.text,
        }

        return data_info

    @staticmethod
    @builder_decorator
    def build_message_info_by_query_event(event: CallbackQueryEventDTO, view_type: int = None):
        assert isinstance(event, CallbackQueryEventDTO)
        chat_info = InfoBuilder.build_chat_info(event)

        data_info = {
            'chat': chat_info,
            'event': {
                'type': event.query_event.__class__.__name__,
                'object_data': event.query_event.to_dict()
            }
        }

        return data_info

    @staticmethod
    @builder_decorator
    def build_message_info_by_chat_action(event: ChatActionEventDTO, view_type: int = None):
        assert isinstance(event, ChatActionEventDTO)

        data_info = {
            'event': {
                'user_ids': event.user_ids,
                'user_added': event.user_added,
                'user_joined': event.user_joined,
                'new_title': event.new_title,
            }
        }

        return data_info

    @staticmethod
    def build_chat_info(event: EventDTO):
        chat_info = None

        if isinstance(event, (MessageEventDTO, CallbackQueryEventDTO)):
            match event.chat_type:
                case 'Chat' | 'Channel':
                    chat_info = {
                        'id': event.chat.id,
                        'title': event.chat.title,
                        'type': event.chat_type,
                        'sender': {
                            'id': event.sender.id,
                            'username': event.sender.username,
                        },
                        'input_peer': event.telegram_event.input_chat.to_dict()
                    }
                case 'User':
                    chat_info = {
                        'id': event.chat.id,
                        'username': event.chat.username,
                        'type': event.chat.__class__.__name__,
                    }

        return chat_info

    @staticmethod
    @builder_decorator
    def build_entity_info(entity, view_type: int = None):
        match entity.__class__.__name__:
            case 'Chat' | 'Channel':
                data_info = {
                    'id': entity.id,
                    'title': entity.title,
                    'type': entity.__class__.__name__,
                }
            case 'User':
                data_info = {
                    'id': entity.id,
                    'username': entity.username,
                    'type': entity.__class__.__name__,
                }
            case _:
                data_info = None

        return data_info

    @staticmethod
    @builder_decorator
    def build_debug_message_info(entity, message, reply_to: Message):
        match entity.__class__.__name__:
            case 'Chat' | 'Channel':
                entity_info = {
                    'id': entity.id,
                    'title': entity.title,
                    'type': entity.__class__.__name__,
                }
            case 'User':
                entity_info = {
                    'id': entity.id,
                    'username': entity.username,
                    'type': entity.__class__.__name__,
                }
            case _:
                entity_info = entity.__class__.__name__

        if reply_to:
            reply_info = {
                'id': reply_to.id,
                'message': reply_to.message,
                'sender_id': reply_to.sender.id,
                'sender_username': reply_to.sender.username
            }
        else:
            reply_info = None

        if isinstance(message, str):
            message = message.replace('\n', '\n ')
        else:
            message = message.__class__.__name__

        data_info = {
            'entity': entity_info,
            'message': message,
            'reply_to': reply_info
        }
        return data_info

    @staticmethod
    def build_about_info(bot):
        return f"{bot.user.first_name} Bot (@{bot.user.username})\n" \
               f"{bot.about}\n" \
               f"Version: {config.VERSION}\n" \
               f"Build: {config.BUILD}"


class Helper:
    MONTHS = ['январь', 'февраль', 'март', 'апрель', 'май', 'июнь',
           'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь']
    COLLECT_RETURN_ONLY_TG = 1
    COLLECT_RETURN_ONLY_DB = 2

    @staticmethod
    def make_member_name(member, with_username: bool = True, with_mention: bool = False):
        full_name = f"{member.first_name or ''} {member.last_name or ''}".strip()
        member_name = full_name

        if with_mention:
            if with_username and member.username:
                member_name += f" (@{member.username})"
            else:
                member_name = f"[{full_name}](tg://user?id={str(member.id)})"
        elif not with_mention and with_username and member.username:
            member_name += f" (__{member.username}__)"

        return member_name

    @staticmethod
    async def make_members_names_string(client, members: list, with_username: bool = True, with_mention: bool = False):
        try:
            members_names = []

            for member in members:
                members_names.append(Helper.make_member_name(
                    await member.get_telegram_member(client),
                    with_username=with_username,
                    with_mention=with_mention
                ))

            return ', '.join(members_names)
        except AttributeError:
            return ''

    # TODO добавить возможность возвращать ассоциативный массив
    @staticmethod
    def collect_members(tg_members: Iterable, db_members: Iterable, flag: int = None) -> Union[list, None]:
        try:
            tmp_tg_members = {}
            for tg_member in tg_members:
                tmp_tg_members[tg_member.id] = tg_member

            result = []
            for db_member in db_members:
                telegram_id = db_member.get_telegram_id()
                if telegram_id in tmp_tg_members:
                    match flag:
                        case Helper.COLLECT_RETURN_ONLY_TG:
                            result.append(tmp_tg_members[telegram_id])
                        case Helper.COLLECT_RETURN_ONLY_DB:
                            result.append(db_member)
                        case _:
                            result.append((tmp_tg_members[telegram_id], db_member))
            return result
        except AttributeError:
            return None

    @staticmethod
    def make_count_str(count: int, advanced_count: int = None) -> str:
        dozens = count % 100
        units = count % 10

        if 10 < dozens < 20:
            count_word = 'раз'
        else:
            if units in range(2, 5):
                count_word = 'раза'
            else:
                count_word = 'раз'

        if advanced_count is None:
            advanced_count_msg = ''
        else:
            advanced_count_msg = f' / {advanced_count}'

        return f'{count}' + advanced_count_msg + f' {count_word}'

    @staticmethod
    def make_buttons_layout(data: list, closing_button: tuple = None):
        buttons = []
        buttons_line = []
        for text, event in data:
            buttons_line.append(Button.inline(text, event))
            if len(buttons_line) == 2:
                buttons.append(buttons_line.copy())
                buttons_line = []
        if buttons_line:
            buttons.append(buttons_line.copy())
        if closing_button and len(closing_button) >= 2:
            buttons.append([Button.inline(closing_button[0], closing_button[1])])
        return buttons

    @staticmethod
    def inflect_word(word, grammemes):
        inflected_word = MorphAnalyzer(lang='ru').parse(word)[0].inflect(grammemes)

        if inflected_word:
            result = inflected_word.word
        else:
            result = word

        return result

    @staticmethod
    def get_words_lexeme(**kwargs) -> dict:
        string_format = {}

        for key, word in kwargs.items():
            string_format[key] = word

            if word.isupper():
                word_case = 'upper'
            elif word.islower():
                word_case = 'lower'
            elif word.istitle():
                word_case = 'capitalize'
            else:
                word_case = None

            parsed_word = MorphAnalyzer(lang='ru').parse(word)[0]

            for lexeme_item in parsed_word.lexeme:
                lexeme_key = f'{key}_{lexeme_item.tag.case}_{lexeme_item.tag.number}'
                lexeme_key = lexeme_key.rstrip('_')

                match word_case:
                    case 'upper':
                        lexeme_word = lexeme_item.word.upper()
                    case 'lower':
                        lexeme_word = lexeme_item.word.lower()
                    case 'capitalize':
                        lexeme_word = lexeme_item.word.capitalize()
                    case _:
                        lexeme_word = lexeme_item.word

                string_format[lexeme_key] = lexeme_word

        return string_format

    @staticmethod
    def get_month_name(month: int = None, grammemes = None):
        if not month:
            month = datetime.now().month

        month_name = Helper.MONTHS[month - 1]

        if grammemes:
            result = Helper.inflect_word(month_name, grammemes)
        else:
            result = month_name

        return result


class ReturnedThread(Thread):
    TIMEOUT = 60
    result = None
    logger = logging.getLogger('main')

    def run(self):
        try:
            if self._target is not None:
                self.result = self._target(*self._args, **self._kwargs)
                self.logger.info(f'Thread result: {self.result}')
        finally:
            del self._target, self._args, self._kwargs

    def join(self, timeout=TIMEOUT):
        super().join(timeout)
