# !/usr/bin/env python

import json

from telethon.tl.types import InputPeerUser, InputPeerChat, InputPeerChannel

from fsb.db.models import Chat, User, Member
from fsb.helpers import Helper
from fsb.telegram.client import TelegramApiClient


class Repository:
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
                name = entity.name
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
