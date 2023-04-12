# !/usr/bin/env python

import json
import sys
from datetime import datetime
from typing import Union

from peewee import (
    AutoField,
    DoesNotExist,
    CharField,
    CompositeKey,
    DateTimeField,
    DeferredForeignKey,
    ForeignKeyField,
    IntegerField,
    Model,
    TextField,
    BooleanField,
    ManyToManyField,
    DeferredThroughModel,
)

from fsb.db import base_db
from fsb.errors import InputValueError


class BaseModel(Model):
    TABLE_NAME = ''

    class Meta:
        @staticmethod
        def make_table_name(model_class):
            if model_class.TABLE_NAME:
                return model_class.TABLE_NAME
            else:
                return model_class.__name__.lower() + 's'

        database = base_db
        table_function = make_table_name

    def save_get_id(self, *args, **kwargs):
        super().save(*args, **kwargs)
        return super().get_id()


class User(BaseModel):
    TABLE_NAME = 'users'

    id = AutoField()
    telegram_id = IntegerField(unique=True)
    name = CharField(null=True)
    nickname = CharField(null=True)
    phone = CharField(null=True)
    input_peer = TextField(null=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.telegram_member = None

    @staticmethod
    def get_by_telegram_id(telegram_id: Union[int, str]) -> 'User':
        return User.get(User.telegram_id == telegram_id)

    async def get_telegram_member(self, client):
        if self.telegram_member is None:
            self.telegram_member = await client.get_entity(self.telegram_id)

        return self.telegram_member


MemberDeferred = DeferredThroughModel()


class Chat(BaseModel):
    TABLE_NAME = 'chats'

    CHAT_TYPE = 1
    CHANNEL_TYPE = 2
    USER_TYPE = 3

    id = AutoField()
    telegram_id = IntegerField(unique=True)
    name = CharField(null=True)
    type = IntegerField()
    input_peer = TextField(null=True)
    dude = BooleanField(default=False)
    users = ManyToManyField(User, backref='chats', through_model=MemberDeferred)

    @staticmethod
    def get_chat_type(chat):
        match chat.__class__.__name__:
            case 'Chat':
                chat_type = Chat.CHAT_TYPE
            case 'Channel':
                chat_type = Chat.CHANNEL_TYPE
            case 'User':
                chat_type = Chat.USER_TYPE
            case _:
                chat_type = 0

        return chat_type

    @staticmethod
    def get_by_telegram_id(telegram_id: Union[int, str]) -> 'Chat':
        return Chat.get(Chat.telegram_id == telegram_id)


class Member(BaseModel):
    TABLE_NAME = 'chats_members'

    id = AutoField()
    chat = ForeignKeyField(Chat, backref='members')
    user = ForeignKeyField(User, backref='chats_members')
    rang = CharField(null=True)

    def get_telegram_id(self):
        telegram_id = None
        if self.user:
            telegram_id = self.user.telegram_id
        return telegram_id

    async def get_telegram_member(self, client):
        return await self.user.get_telegram_member(client)


MemberDeferred.set_model(Member)


class Role(BaseModel):
    TABLE_NAME = 'roles'

    id = AutoField()
    name = CharField(null=True)
    nickname = CharField(null=True)
    chat = ForeignKeyField(Chat)

    @staticmethod
    def parse_from_message(message: str) -> tuple:
        message = message.split(',')

        if len(message) >= 2:
            name = message[0].strip(' \n\t')
            nickname = message[1].strip('@ \n\t')
        elif len(message) >= 1:
            name = nickname = message[0].strip('@ \n\t')
        else:
            name = nickname = None

        if not name or not nickname or '@' in nickname:
            raise InputValueError

        return name, nickname

    @staticmethod
    def find_by_chat(chat: Chat):
        return Role.select().where(Role.chat == chat)


class MemberRole(BaseModel):
    TABLE_NAME = 'chats_members_roles'

    class Meta:
        primary_key = CompositeKey('member', 'role')

    member = ForeignKeyField(Member)
    role = ForeignKeyField(Role, on_delete='CASCADE')

    def get_telegram_id(self):
        telegram_id = None
        if self.member:
            telegram_id = self.member.user.telegram_id
        return telegram_id

    async def get_telegram_member(self, client):
        return await self.member.user.get_telegram_member(client)


class Rating(BaseModel):
    TABLE_NAME = 'ratings'

    id = AutoField()
    name = CharField()
    chat = ForeignKeyField(Chat)
    command = CharField()
    last_run = DateTimeField(null=True)
    last_month_run = DateTimeField(null=True)
    last_winner = DeferredForeignKey('RatingMember', null=True, on_delete='SET NULL')
    last_month_winner = DeferredForeignKey('RatingMember', null=True, on_delete='SET NULL')
    autorun = BooleanField(default=False)

    @staticmethod
    def parse_from_message(message: str) -> tuple:
        message = message.split(',')

        if len(message) >= 2:
            command = message[0].strip(' \n\t').lower()
            name = message[1].strip(' \n\t')
        elif len(message) >= 1:
            command = name = message[0].strip(' \n\t')
            command = command.lower()
        else:
            name = command = None

        if not name or not command:
            raise InputValueError

        return command, name

    def get_non_winners(self, is_month: bool = False):
        result = []
        rating_winner_attr = Rating.last_month_winner_id if is_month else Rating.last_winner_id

        for rating_member in self.members:
            if (not rating_member
                    .member
                    .ratings_members
                    .join(Rating, on=(rating_winner_attr == RatingMember.id))
                    .exists()):
                result.append(rating_member)

        return result


class RatingMember(BaseModel):
    TABLE_NAME = 'ratings_members'

    id = AutoField()
    member = ForeignKeyField(Member, on_delete='CASCADE', backref='ratings_members')
    rating = ForeignKeyField(Rating, on_delete='CASCADE', backref='members')
    total_count = IntegerField(default=0)
    month_count = IntegerField(default=0)
    current_month_count = IntegerField(default=0)
    created_at = DateTimeField(default=datetime.now())

    def get_telegram_id(self):
        telegram_id = None
        if self.member:
            telegram_id = self.member.user.telegram_id
        return telegram_id

    async def get_telegram_member(self, client):
        return await self.member.user.get_telegram_member(client)


class QueryEvent(BaseModel):
    TABLE_NAME = 'query_events'

    id = AutoField()
    module_name = CharField(null=True, default='module')
    class_name = CharField(null=True, default='class')
    data = TextField(null=True)
    created_at = DateTimeField(default=datetime.now())

    def __init__(self, sender_id: int = None, data_value=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sender_id = sender_id
        self._data_value = data_value
        if '__no_default__' not in kwargs:
            self.module_name = self.__class__.__module__
            self.class_name = self.__class__.__name__
            self.data = json.dumps(self.to_dict())

    def build_data_dict(self) -> dict:
        if isinstance(self._data_value, dict):
            result = self._data_value
        else:
            result = {}
        return result

    def to_dict(self) -> dict:
        return {
            'sender_id': self.sender_id,
            'data': self._data_value
        }

    @classmethod
    def normalize_data_dict(cls, data_dict: dict) -> dict:
        if 'sender_id' not in data_dict:
            data_dict['sender_id'] = None
        if 'data' not in data_dict:
            data_dict['data'] = None
        return data_dict

    @classmethod
    def from_dict(cls, data_dict: dict) -> 'QueryEvent':
        data_dict = cls.normalize_data_dict(data_dict)
        return cls(data_dict['sender_id'], data_dict['data'])

    @classmethod
    def find_and_create(cls, id: int) -> Union['QueryEvent', None]:
        try:
            query_event = cls.get_by_id(id)
            assert query_event.module_name and query_event.class_name
        except DoesNotExist or AssertionError:
            return None

        data_dict = {}
        if query_event.data:
            data_dict = json.loads(query_event.data)
        instance_class = getattr(
            sys.modules[query_event.module_name],
            query_event.class_name
        )

        if issubclass(instance_class, QueryEvent):
            instance = instance_class.from_dict(data_dict)
        else:
            instance = None

        return instance


class CacheQuantumRand(BaseModel):
    TABLE_NAME = 'cache_quantum_rand'

    value = IntegerField(null=False)
    range = CharField(null=True)
    created_at = DateTimeField(default=datetime.now())
