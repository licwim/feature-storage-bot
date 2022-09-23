# !/usr/bin/env python

import json
from typing import Union, Iterable

import yaml
from telethon.tl.custom.button import Button
from telethon.tl.patched import Message

from fsb import BUILD
from fsb import VERSION
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
            }
        }

        return data_info

    @staticmethod
    def build_chat_info(event: EventDTO):
        chat_info = None

        if isinstance(event, (MessageEventDTO, CallbackQueryEventDTO)):
            match event.chat_type:
                case 'Chat':
                    chat_info = {
                        'id': event.chat.id,
                        'name': event.chat.name,
                        'type': event.chat_type,
                        'sender': {
                            'id': event.sender.id,
                            'username': event.sender.username,
                        },
                        'input_peer': event.telegram_event.input_chat.to_dict()
                    }
                case 'Channel':
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
            case 'Chat':
                data_info = {
                    'id': entity.id,
                    'name': entity.name,
                    'type': entity.__class__.__name__,
                }
            case 'Channel':
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
            case 'Chat':
                entity_info = {
                    'id': entity.id,
                    'name': entity.name,
                    'type': entity.__class__.__name__,
                }
            case 'Channel':
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
                entity_info = None

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
               f"Version: {VERSION}\n" \
               f"Build: {BUILD}"


class Helper:
    @staticmethod
    def make_member_name(member, with_username: bool = True, with_mention: bool = False):
        first_name = member.first_name if member.first_name else ''
        last_name = f" {member.last_name}" if member.last_name else ''
        if with_username and member.username:
            if with_mention:
                username = f" (@{member.username})"
            else:
                username = f" (__{member.username}__)"
        else:
            username = ''
        return f"{first_name}{last_name}{username}"

    # TODO добавить возможность возвращать ассоциативный массив
    @staticmethod
    def collect_members(tg_members: Iterable, db_members: Iterable) -> Union[list, None]:
        try:
            tmp_tg_members = {}
            for tg_member in tg_members:
                tmp_tg_members[tg_member.id] = tg_member

            result = []
            for db_member in db_members:
                telegram_id = db_member.get_telegram_id()
                if telegram_id in tmp_tg_members:
                    result.append((tmp_tg_members[telegram_id], db_member))
            return result
        except AttributeError:
            return None

    @staticmethod
    def make_count_str(count: int) -> str:
        dozens = count % 100
        units = count % 10
        if 10 < dozens < 20:
            count_word = 'раз'
        else:
            if units in range(2, 5):
                count_word = 'раза'
            else:
                count_word = 'раз'
        return f"{str(count)} {count_word}"

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
