# !/usr/bin/env python

import inspect

from telethon.events.callbackquery import CallbackQuery
from telethon.events.chataction import ChatAction
from telethon.events.common import EventCommon
from telethon.events.messageedited import MessageEdited
from telethon.events.newmessage import NewMessage


class EventDTO:
    # Handlers areas
    ALL = 0
    ONLY_CHAT = 1
    ONLY_USER = 2

    def __init__(self, event):
        assert isinstance(event, EventCommon)
        self.telegram_event = event
        self.chat = event.chat
        self.chat_type = event.chat.__class__.__name__
        self.debug = False
        self.area = self.ALL

        from fsb.db.models import Module
        self.module_name = Module.MODULE_DEFAULT

    def get_attributes(self):
        attributes = {}
        for m in inspect.getmembers(self):
            if not m[0].startswith('_'):
                if not inspect.ismethod(m[1]) and not inspect.isfunction(m[1]):
                    attributes.update([m])
        return attributes


class MessageEventDTO(EventDTO):
    def __init__(self, event):
        assert isinstance(event, NewMessage.Event) or isinstance(event, MessageEdited.Event)
        super().__init__(event)
        self.message = event.message
        self.sender = event.sender


class CallbackQueryEventDTO(EventDTO):
    def __init__(self, event):
        assert isinstance(event, CallbackQuery.Event)
        super().__init__(event)
        self.data = event.data
        self.query_event = None
        self.source_message_id = event.query.msg_id
        self.sender = event.sender
        self.query_event_class = None


class MenuEventDTO(CallbackQueryEventDTO):
    def __init__(self, event):
        super().__init__(event)
        self.menu_message = None


class ChatActionEventDTO(EventDTO):
    def __init__(self, event):
        assert isinstance(event, ChatAction.Event)
        super().__init__(event)
        self.user_ids = event.user_ids
        self.user_joined = event.user_joined
        self.user_added = event.user_added
        self.new_title = event.new_title


class CommandEventDTO(MessageEventDTO):
    def __init__(self, event):
        super().__init__(event)
        self.command = None
        self.args = []
        self.command_names = []


class MentionEventDTO(MessageEventDTO):
    def __init__(self, event):
        super().__init__(event)
        self.mentions = []
