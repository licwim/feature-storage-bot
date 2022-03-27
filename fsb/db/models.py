# !/usr/bin/env python
import json
import sys
from datetime import datetime

from peewee import AutoField
from peewee import CharField
from peewee import CompositeKey
from peewee import DateTimeField
from peewee import ForeignKeyField
from peewee import IntegerField
from peewee import Model
from peewee import TextField

from fsb.db import base_db
from fsb.error import InputValueError


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


class Chat(BaseModel):
    TABLE_NAME = 'chats'

    CHAT_TYPE = 1
    CHANNEL_TYPE = 2
    USER_TYPE = 3

    id = AutoField()
    telegram_id = IntegerField(unique=True)
    name = CharField(null=True)
    type = IntegerField()

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


class Member(BaseModel):
    TABLE_NAME = 'chats_members'

    id = AutoField()
    chat = ForeignKeyField(Chat)
    user = ForeignKeyField(User)
    rang = CharField(null=True)


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
            name = nickname = message[0]
        else:
            name = nickname = None

        if not name or not nickname or '@' in nickname:
            raise InputValueError

        return name, nickname


class MemberRole(BaseModel):
    TABLE_NAME = 'chats_members_roles'

    class Meta:
        primary_key = CompositeKey('member', 'role')

    member = ForeignKeyField(Member)
    role = ForeignKeyField(Role, on_delete='CASCADE')


class Rating(BaseModel):
    TABLE_NAME = 'ratings'

    id = AutoField()
    name = CharField(null=True)
    command = CharField(null=True)
    chat = ForeignKeyField(Chat)


class RatingMember(BaseModel):
    TABLE_NAME = 'ratings_members'

    id = AutoField()
    member = ForeignKeyField(Member)
    rating = ForeignKeyField(Rating)
    times = IntegerField(default=0)
    created_at = DateTimeField(default=datetime.now())


class QueryEvent(BaseModel):
    TABLE_NAME = 'query_events'

    id = AutoField()
    module_name = CharField(null=True, default='module')
    class_name = CharField(null=True, default='class')
    data = TextField(null=True)
    created_at = DateTimeField(default=datetime.now())

    def __init__(self, data_value=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if '__no_default__' not in kwargs:
            self.module_name = self.__class__.__module__
            self.class_name = self.__class__.__name__
            self.data = json.dumps({'data': data_value})

    def to_dict(self):
        return {}

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data)

    @classmethod
    def find_and_create(cls, id: int):
        query_event = cls.get_by_id(id)

        if not query_event.module_name or not query_event.class_name:
            return query_event

        data = None
        if query_event.data:
            data_dict = json.loads(query_event.data)
            if 'data' in data_dict:
                data = data_dict['data']
        instance = getattr(
            sys.modules[query_event.module_name],
            query_event.class_name
        ).from_dict(data)
        assert isinstance(instance, QueryEvent)
        return instance
