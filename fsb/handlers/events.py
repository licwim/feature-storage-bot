# !/usr/bin/env python

from telethon.events.callbackquery import CallbackQuery
from telethon.events.chataction import ChatAction
from telethon.events.common import EventCommon
from telethon.events.messageedited import MessageEdited
from telethon.events.newmessage import NewMessage


class EventDTO:
    def __init__(self, event):
        assert isinstance(event, EventCommon)
        self._event = event
        self.chat = event.chat
        self.chat_type = event.chat.__class__.__name__


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


class MenuEventDTO(CallbackQueryEventDTO):
    def __init__(self, event):
        super().__init__(event)
        self.menu_message = None


class ChatActionEventDTO(EventDTO):
    def __init__(self, event):
        assert isinstance(event, ChatAction.Event)
        super().__init__(event)
        self.user_ids = event.user_ids


class CommandEventDTO(MessageEventDTO):
    def __init__(self, event):
        super().__init__(event)
        self.command = None
        self.args = []


class WatcherEventDTO(MessageEventDTO):
    def __init__(self, event):
        super().__init__(event)
