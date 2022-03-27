# !/usr/bin/env python

import json

import yaml
from telethon.events.callbackquery import CallbackQuery
from telethon.events.messageedited import MessageEdited
from telethon.events.newmessage import NewMessage
from telethon.tl.patched import Message


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
    def build_message_info_by_message_event(event, view_type: int = None):
        assert isinstance(event, NewMessage.Event) or isinstance(event, MessageEdited.Event)
        chat_info = InfoBuilder.build_chat_info(event)

        data_info = {
            'chat': chat_info,
            'message': event.message.text,
        }

        return data_info

    @staticmethod
    @builder_decorator
    def build_message_info_by_query_event(event, query_event, view_type: int = None):
        assert isinstance(event, CallbackQuery.Event)
        chat_info = InfoBuilder.build_chat_info(event)

        data_info = {
            'chat': chat_info,
            'event': {
                'type': query_event.__class__.__name__,
                'data': query_event.to_dict()
            }
        }

        return data_info

    @staticmethod
    def build_chat_info(event):
        match event.chat.__class__.__name__:
            case 'Chat' | 'Channel':
                chat_info = {
                    'id': event.chat.id,
                    'title': event.chat.title,
                    'type': event.chat.__class__.__name__,
                    'sender': {
                        'id': event.sender.id,
                        'username': event.sender.username,
                    }
                }
            case 'User':
                chat_info = {
                    'id': event.chat.id,
                    'username': event.chat.username,
                    'type': event.chat.__class__.__name__,
                }
            case _:
                chat_info = None

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
