# !/usr/bin/env python

from typing import Union

from peewee import DoesNotExist

from fsb.db.models import QueryEvent, Chat, Module
from fsb.helpers import Helper


class ModuleQueryEvent(QueryEvent):
    def __init__(self, sender_id: int = None, chat_id: int = None, module_id: str = None):
        self.chat_id = chat_id
        self.chat = None
        self.module_id = module_id
        self.module = None
        super().__init__(sender_id, self.build_data_dict())

    def build_data_dict(self) -> dict:
        return {
            'chat_id': self.chat_id,
            'module_id': self.module_id,
        }

    @classmethod
    def normalize_data_dict(cls, data_dict: dict) -> dict:
        data_dict = super().normalize_data_dict(data_dict)
        for key in ['chat_id', 'module_id']:
            if key not in data_dict['data']:
                data_dict['data'][key] = None
        return data_dict

    @classmethod
    def from_dict(cls, data_dict: dict) -> QueryEvent:
        data_dict = cls.normalize_data_dict(data_dict)
        sender_id = data_dict['sender_id']
        data = data_dict['data']
        return cls(sender_id=sender_id, chat_id=data['chat_id'], module_id=data['module_id'])

    def get_chat(self) -> Union[Chat, None]:
        if not self.chat and self.chat_id:
            self.chat = Chat.get_by_id(self.chat_id)

        return self.chat

    def get_module(self) -> Union[Module, None]:
        if not self.module and self.module_id:
            self.module = Module.get_by_id(self.module_id)

        return self.module


class GeneralMenuModuleEvent(ModuleQueryEvent):
    @staticmethod
    def get_message_and_buttons(sender_id, chat_id, enabled_modules_names) -> tuple:
        buttons = []

        try:
            modules = (Module.select()
                       .where(Module.active and Module.name != Module.MODULE_DEFAULT)
                       .order_by(Module.created_at.asc()))

            for module in modules:
                if module.name in enabled_modules_names:
                    event_class = DisableModuleEvent
                    text = module.get_readable_name() + ': ВКЛ'
                else:
                    event_class = EnableModuleEvent
                    text = module.get_readable_name() + ': ВЫКЛ'

                buttons.append((
                    text,
                    event_class(sender_id=sender_id, chat_id=chat_id, module_id=module.name).save_get_id()
                ))

            buttons = Helper.make_buttons_layout(
                buttons, ('Закрыть', CloseGeneralMenuModuleEvent(sender_id=sender_id).save_get_id())
            )
            message = 'Модули'
        except DoesNotExist:
            message = 'На данный момент все модули не активны'

        return message, buttons


class CloseGeneralMenuModuleEvent(ModuleQueryEvent):
    pass


class EnableModuleEvent(ModuleQueryEvent):
    pass


class DisableModuleEvent(ModuleQueryEvent):
    pass
