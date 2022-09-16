# !/usr/bin/env python

from typing import Union

from telethon import Button

from fsb.db.models import QueryEvent, Role, Member


class RoleQueryEvent(QueryEvent):
    def __init__(self, sender_id: int = None, role_id: int = None, member_id: int = None):
        self.role_id = role_id
        self.role = None
        self.member_id = member_id
        self.member = None
        super().__init__(sender_id, self.build_data_dict())

    def build_data_dict(self) -> dict:
        return {
            'role_id': self.role_id,
            'member_id': self.member_id,
        }

    @classmethod
    def normalize_data_dict(cls, data_dict: dict) -> dict:
        data_dict = super().normalize_data_dict(data_dict)
        for key in ['role_id', 'member_id']:
            if key not in data_dict['data']:
                data_dict['data'][key] = None
        return data_dict

    @classmethod
    def from_dict(cls, data_dict: dict) -> QueryEvent:
        data_dict = cls.normalize_data_dict(data_dict)
        sender_id = data_dict['sender_id']
        data = data_dict['data']
        return cls(sender_id=sender_id, role_id=data['role_id'], member_id=data['member_id'])

    def get_role(self) -> Union[Role, None]:
        if not self.role and self.role_id:
            self.role = Role.get_by_id(self.role_id)

        return self.role

    def get_member(self) -> Union[Member, None]:
        if not self.member and self.member_id:
            self.member = Member.get_by_id(self.member_id)

        return self.member


class GeneralMenuRoleEvent(RoleQueryEvent):
    @staticmethod
    def get_message_and_buttons(sender_id) -> tuple:
        return "Меню ролей", [
            [
                Button.inline('Список ролей', ListRoleEvent(sender_id).save_get_id())
            ],
            [
                Button.inline('Создать роль', CreateRoleEvent(sender_id).save_get_id()),
                Button.inline('Удалить роль', DeleteMenuRoleEvent(sender_id).save_get_id()),
            ],
            [
                Button.inline('Закрыть', CloseGeneralMenuRoleEvent(sender_id).save_get_id())
            ]
        ]


class CreateRoleEvent(RoleQueryEvent):
    pass


class ListRoleEvent(RoleQueryEvent):
    pass


class DeleteMenuRoleEvent(RoleQueryEvent):
    pass


class MenuRoleEvent(RoleQueryEvent):
    pass


class DeleteRoleEvent(RoleQueryEvent):
    pass


class ChangeRoleEvent(RoleQueryEvent):
    pass


class TruncateRoleEvent(RoleQueryEvent):
    pass


class ListMembersRoleEvent(RoleQueryEvent):
    pass


class AddMemberMenuRoleEvent(RoleQueryEvent):
    pass


class AddMemberRoleEvent(RoleQueryEvent):
    pass


class RemoveMemberMenuRoleEvent(RoleQueryEvent):
    pass


class RemoveMemberRoleEvent(RoleQueryEvent):
    pass


class CloseGeneralMenuRoleEvent(RoleQueryEvent):
    pass
