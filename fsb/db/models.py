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
    BigIntegerField,
    TextField,
    BooleanField,
    ManyToManyField,
    DeferredThroughModel,
    DateField,
    SQL,
)

from fsb.db import database as base_db, ModelInterface
from fsb.db.helpers import DirtyModel, DirtyModelState
from fsb.db.traits import CreatedUpdatedAtTrait, CreatedAtTrait, DeletedAtWithReasonTrait, DeletedAtTrait
from fsb.errors import InputValueError


class BaseModel(ModelInterface):
    TABLE_NAME = ''
    _real_dirty = DirtyModelState()

    class Meta:
        @staticmethod
        def make_table_name(model_class):
            if model_class.TABLE_NAME:
                return model_class.TABLE_NAME
            else:
                return model_class.__name__.lower() + 's'

        database = base_db
        table_function = make_table_name
        only_save_dirty = True

    def save_get_id(self, *args, **kwargs):
        super().save(*args, **kwargs)
        return super().get_id()

    def __setattr__(self, key, value):
        if self._real_dirty.is_dirty() and key in self._meta.fields and getattr(self, key) == value:
            return
        super().__setattr__(key, value)

    def save(self, *args, **kwargs):
        if self._real_dirty.is_dirty() and self.is_dirty():
            super().save(only=self.dirty_fields, *args, **kwargs)
        elif not self._real_dirty.is_dirty():
            super().save(*args, **kwargs)

    def dirty(self):
        return DirtyModel(self._real_dirty)

    @classmethod
    def with_enabled_module(cls, module_name: str = None, query=None):
        if not query:
            query = cls.select()

        if not module_name:
            module_name = Module.get_module_name_by_table(cls.TABLE_NAME)

        if module_name:
            if cls == Chat:
                reference_column = cls.id
            else:
                reference_column = cls.chat_id

            query = (query.join(ChatModule, on=(ChatModule.chat_id == reference_column))
                     .join(Module, on=(Module.name == ChatModule.module_id))
                     .where(Module.active and ChatModule.module_id == module_name))

        return query

    def is_enabled_module(self, module_name: str) -> bool:
        return self.with_enabled_module(module_name).exists()

    @classmethod
    def find_by_chat(cls, chat: 'Chat', only_active: bool = True):
        try:
            query = cls.select().where(cls.chat == chat)

            if only_active and issubclass(cls, DeletedAtTrait):
                query = query.where(cls.deleted_at.is_null())

            return query
        except AttributeError:
            return None


class TelegramEntity(BaseModel, CreatedUpdatedAtTrait, DeletedAtWithReasonTrait):

    telegram_id = BigIntegerField(unique=True)
    input_peer = TextField(null=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.telegram_member = None

    async def get_telegram_member(self, client):
        if self.telegram_member is None:
            self.telegram_member = await client.get_entity(self.telegram_id)

        return self.telegram_member

    @classmethod
    def get_by_telegram_id(cls, telegram_id: Union[int, str]):
        return cls.get_or_none(cls.telegram_id == telegram_id)


class User(TelegramEntity):
    TABLE_NAME = 'users'

    id = AutoField()
    name = CharField(null=True)
    nickname = CharField(null=True)
    phone = CharField(null=True)
    birthday = DateField(null=True)


MemberDeferred = DeferredThroughModel()


class Chat(TelegramEntity):
    TABLE_NAME = 'chats'

    CHAT_TYPE = 1
    CHANNEL_TYPE = 2
    USER_TYPE = 3

    id = AutoField()
    name = CharField(null=True)
    type = IntegerField()
    users = ManyToManyField(User, backref='chats', through_model=MemberDeferred)

    @staticmethod
    def get_chat_type(chat):
        match chat.__class__.__name__:
            case 'Chat'|'ChatForbidden':
                chat_type = Chat.CHAT_TYPE
            case 'Channel'|'ChannelForbidden':
                chat_type = Chat.CHANNEL_TYPE
            case 'User':
                chat_type = Chat.USER_TYPE
            case _:
                chat_type = 0

        return chat_type

    def enable_module(self, module_name):
        return ChatModule.get_or_create(chat=self, module_id=module_name)

    def disable_module(self, module_name):
        chat_module = ChatModule.get(ChatModule.chat == self, ChatModule.module_id == module_name)

        if isinstance(chat_module, ChatModule):
            return chat_module.delete_instance()

    def mark_as_deleted(self, reason = None):
        super().mark_as_deleted(reason)

        CronJob.update(active=False).where(CronJob.chat == self).execute()
        ChatModule.delete().where(ChatModule.chat == self).execute()

        self.save()

    def mark_as_undeleted(self):
        super().mark_as_undeleted()

        self.enable_module(Module.MODULE_DEFAULT)

        self.save()


class Member(BaseModel, CreatedUpdatedAtTrait, DeletedAtWithReasonTrait):
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


class Role(BaseModel, CreatedUpdatedAtTrait):
    TABLE_NAME = 'roles'

    id = AutoField()
    name = CharField(null=True)
    nickname = CharField(null=True)
    chat = ForeignKeyField(Chat, backref='roles')

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


class MemberRole(BaseModel, CreatedUpdatedAtTrait):
    TABLE_NAME = 'chats_members_roles'

    class Meta:
        primary_key = CompositeKey('member', 'role')

    member = ForeignKeyField(Member, backref='roles_members')
    role = ForeignKeyField(Role, backref='members', on_delete='CASCADE')

    def get_telegram_id(self):
        telegram_id = None
        if self.member:
            telegram_id = self.member.user.telegram_id
        return telegram_id

    async def get_telegram_member(self, client):
        return await self.member.user.get_telegram_member(client)


class Rating(BaseModel, CreatedUpdatedAtTrait):
    TABLE_NAME = 'ratings'

    id = AutoField()
    name = CharField()
    chat = ForeignKeyField(Chat, backref='ratings')
    command = CharField()
    last_run = DateTimeField(null=True)
    last_month_run = DateTimeField(null=True)
    last_year_run = DateTimeField(null=True)
    last_winner = DeferredForeignKey('RatingMember', null=True, on_delete='SET NULL')
    last_month_winner = DeferredForeignKey('RatingMember', null=True, on_delete='SET NULL')
    last_year_winner = DeferredForeignKey('RatingMember', null=True, on_delete='SET NULL')
    autorun = BooleanField(default=False, constraints=[SQL('DEFAULT 0')])

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

        if is_month:
            rating_winner_attr = Rating.last_month_winner_id
            date_exp = (Rating.last_month_run >= datetime.today().replace(hour=0, minute=0, second=0, microsecond=0, day=1))
        else:
            rating_winner_attr = Rating.last_winner_id
            date_exp = (Rating.last_run >= datetime.today().replace(hour=0, minute=0, second=0, microsecond=0))

        for rating_member in self.members.order_by(RatingMember.id):
            if (not rating_member
                    .member
                    .ratings_members
                    .join(Rating, on=(rating_winner_attr == RatingMember.id))
                    .where(date_exp)
                    .exists()):
                result.append(rating_member)

        return result


class RatingMember(BaseModel, CreatedUpdatedAtTrait):
    TABLE_NAME = 'ratings_members'

    id = AutoField()
    member = ForeignKeyField(Member, on_delete='CASCADE', backref='ratings_members')
    rating = ForeignKeyField(Rating, on_delete='CASCADE', backref='members')
    total_count = IntegerField(default=0, constraints=[SQL('DEFAULT 0')])
    month_count = IntegerField(default=0, constraints=[SQL('DEFAULT 0')])
    current_month_count = IntegerField(default=0, constraints=[SQL('DEFAULT 0')])
    current_year_count = IntegerField(default=0)

    def get_telegram_id(self):
        telegram_id = None
        if self.member:
            telegram_id = self.member.user.telegram_id
        return telegram_id

    async def get_telegram_member(self, client):
        return await self.member.user.get_telegram_member(client)


class QueryEvent(BaseModel, CreatedAtTrait):
    TABLE_NAME = 'query_events'

    id = AutoField()
    module_name = CharField(null=True, default='module', constraints=[SQL('DEFAULT "module"')])
    class_name = CharField(null=True, default='class', constraints=[SQL('DEFAULT "class"')])
    data = TextField(null=True)
    last_usage_date = DateTimeField(null=True)

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


class RatingLeader(BaseModel, CreatedAtTrait):
    TABLE_NAME = 'ratings_leaders'

    id = AutoField()
    rating_member = ForeignKeyField(RatingMember, backref='leaders', on_delete='CASCADE', on_update='CASCADE')
    date = DateField(null=False)
    chat = ForeignKeyField(Chat, backref='ratings_leaders', on_update='CASCADE', on_delete='CASCADE')


class CacheQuantumRand(BaseModel):
    TABLE_NAME = 'cache_quantum_rand'

    id = AutoField()
    value = IntegerField(null=False)
    type = CharField(null=False, default='uint16', constraints=[SQL('DEFAULT "uint16"')])


class Module(BaseModel):
    TABLE_NAME = 'modules'

    MODULE_DEFAULT = 'default'
    MODULE_ROLES = 'roles'
    MODULE_RATINGS = 'ratings'
    MODULE_DUDE = 'dude'
    MODULE_HAPPY_NEW_YEAR = 'happy_new_year'
    MODULE_BIRTHDAY = 'birthday'
    MODULE_CRON = 'cron'

    MODULES_LIST = [
        MODULE_DEFAULT,
        MODULE_ROLES,
        MODULE_RATINGS,
        MODULE_DUDE,
        MODULE_HAPPY_NEW_YEAR,
        MODULE_BIRTHDAY,
        MODULE_CRON,
    ]

    name = CharField(null=False, primary_key=True)
    readable_name = CharField(null=True)
    active = BooleanField(null=False, default=True, constraints=[SQL('DEFAULT 1')])
    sort = IntegerField(null=False)

    @staticmethod
    def get_module_name_by_table(table):
        modules_by_tables = {
            Role.TABLE_NAME: Module.MODULE_ROLES,
            Rating.TABLE_NAME: Module.MODULE_RATINGS,
        }

        return modules_by_tables.get(table)

    def get_readable_name(self):
        return self.readable_name if self.readable_name else self.name


class ChatModule(BaseModel, CreatedAtTrait):
    TABLE_NAME = 'chats_modules'

    class Meta:
        primary_key = CompositeKey('chat', 'module')

    chat = ForeignKeyField(Chat, backref='chat_modules', on_delete='CASCADE', on_update='CASCADE')
    module = ForeignKeyField(Module, backref='module_chats', on_delete='CASCADE', on_update='CASCADE')


class CronJob(BaseModel, CreatedUpdatedAtTrait):
    TABLE_NAME = 'cron_jobs'

    id = AutoField()
    name = CharField(null=False)
    chat = ForeignKeyField(Chat, backref='cron_jobs', on_delete='CASCADE', on_update='CASCADE')
    message = CharField(null=False)
    schedule = CharField(null=False)
    active = BooleanField(null=False, default=True, constraints=[SQL('DEFAULT 1')])
