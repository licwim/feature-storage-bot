# !/usr/bin/env python

from datetime import datetime

from peewee import AutoField
from peewee import CharField
from peewee import CompositeKey
from peewee import DateTimeField
from peewee import ForeignKeyField
from peewee import IntegerField
from peewee import Model

from fsb.db import base_db


class BaseModel(Model):
    TABLE_NAME = ''

    class Meta:
        @staticmethod
        def make_table_name(model_class):
            if model_class.TABLE_NAME:
                return model_class.TABLE_NAME
            else:
                return model_class.__name__.lower()

        database = base_db
        table_function = make_table_name


class User(BaseModel):
    TABLE_NAME = 'users'

    id = AutoField()
    telegram_id = IntegerField()
    name = CharField(null=True)
    nickname = CharField(null=True)
    phone = CharField(null=True)


class Chat(BaseModel):
    TABLE_NAME = 'chats'

    id = AutoField()
    telegram_id = IntegerField()
    name = CharField(null=True)
    type = IntegerField()


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


class MemberRole(BaseModel):
    TABLE_NAME = 'chats_members_roles'

    class Meta:
        primary_key = CompositeKey('member', 'role')

    member = ForeignKeyField(Member)
    role = ForeignKeyField(Role)


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
