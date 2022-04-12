# !/usr/bin/env python

from asyncio.exceptions import TimeoutError
from typing import Union

from inflection import underscore
from telethon import events
from telethon.tl.custom.button import Button

from fsb.db.models import Chat
from fsb.db.models import Member
from fsb.db.models import MemberRole
from fsb.db.models import QueryEvent
from fsb.db.models import Role
from fsb.db.models import User
from fsb.error import ConversationTimeoutError
from fsb.error import InputValueError
from fsb.handlers import BaseMenu
from fsb.handlers import Handler
from fsb.handlers.commands import BaseCommand
from fsb.telegram.client import TelegramApiClient


class RoleQueryEvent(QueryEvent):
    def __init__(self, sender: int = None, role_id: int = None, member_id: int = None):
        self.role_id = role_id
        self.role = None
        self.member_id = member_id
        self.member = None
        super().__init__(sender, self.build_data_dict())

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
        sender = data_dict['sender']
        data = data_dict['data']
        return cls(sender=sender, role_id=data['role_id'], member_id=data['member_id'])

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
    def get_message_and_buttons(sender) -> tuple:
        return "Меню ролей", [
            [
                Button.inline('Список ролей', ListRoleEvent(sender).save_get_id())
            ],
            [
                Button.inline('Создать роль', CreateRoleEvent(sender).save_get_id()),
                Button.inline('Удалить роль', DeleteMenuRoleEvent(sender).save_get_id()),
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


class RolesSettingsCommand(BaseCommand):
    def __init__(self, client: TelegramApiClient):
        super().__init__(client, 'roles')
        self._area = self.ONLY_CHAT

    @Handler.handle_decorator
    async def handle(self, event):
        await super().handle(event)
        text, buttons = GeneralMenuRoleEvent.get_message_and_buttons(event.message.sender.id)
        await self._client.send_message(self.entity, text, buttons=buttons)


class RolesSettingsQuery(BaseMenu):
    def __init__(self, client: TelegramApiClient):
        super().__init__(client)
        self._area = self.ONLY_CHAT

    @Handler.handle_decorator
    async def handle(self, event):
        await super().handle(event)
        if not isinstance(self.query_event, RoleQueryEvent):
            return

        query_event_type = underscore(self.query_event.__class__.__name__.replace('RoleEvent', ''))
        action = getattr(self, 'action_' + query_event_type)
        if action:
            await action()

    async def action_general_menu(self):
        text, buttons = GeneralMenuRoleEvent.get_message_and_buttons(self._sender)
        await self._menu_message.edit(text, buttons=buttons)

    async def get_role_params(self, conv):
        response = conv.wait_event(
            events.NewMessage(forwards=False, chats=self.entity, from_users=self.event.sender),
            timeout=self.INPUT_TIMEOUT
        )
        await conv.send_message('Введи тег роли либо название и тег через запятую\n(Rolename, roletag)')
        response_event = await response

        name, nickname = Role.parse_from_message(response_event.message.text)

        chat = Chat.get_or_create(
            telegram_id=self.entity.id,
            defaults={
                'name': self.entity.title,
                'type': Chat.get_chat_type(self.entity)
            }
        )[0]

        if Role.get_or_none(Role.chat == chat, Role.nickname == nickname):
            return None
        else:
            return name, nickname, chat

    async def action_create(self):
        async with self._client._client.conversation(self.entity) as conv:
            try:
                params = await self.get_role_params(conv)
                if params:
                    Role.create(name=params[0], nickname=params[1], chat=params[2]).save()
                    await conv.send_message(f"Создана роль: {params[0]} (@{params[1]})")
                else:
                    await conv.send_message("Такая роль уже существует")
                    return
            except TimeoutError:
                await conv.send_message(ConversationTimeoutError.message)
            except InputValueError as ex:
                await conv.send_message(ex.message)

        await self._client._client.send_message(entity=self.entity, message=self._menu_message)

    async def action_list(self, new_message: bool = False):
        chat = Chat.get_or_create(
            telegram_id=self.entity.id,
            defaults={
                'name': self.entity.title,
                'type': Chat.get_chat_type(self.entity)
            }
        )[0]
        roles = Role.select().where(Role.chat == chat)
        buttons = []
        buttons_line = []
        for role in roles:
            buttons_line.append(Button.inline(
                f"{role.name} (@{role.nickname})",
                MenuRoleEvent(self._sender, role.id).save_get_id()
            ))
            if len(buttons_line) == 2:
                buttons.append(buttons_line.copy())
                buttons_line = []
        if buttons_line:
            buttons.append(buttons_line.copy())
        buttons.append([Button.inline("<< К меню ролей", GeneralMenuRoleEvent(self._sender).save_get_id())])
        text = "Список ролей:"
        if new_message:
            await self._client.send_message(self.entity, text, buttons=buttons)
        else:
            await self._menu_message.edit(text, buttons=buttons)

    async def action_delete_menu(self):
        chat = Chat.get_or_create(
            telegram_id=self.entity.id,
            defaults={
                'name': self.entity.title,
                'type': Chat.get_chat_type(self.entity)
            }
        )[0]
        roles = Role.select().where(Role.chat == chat)
        buttons = []
        buttons_line = []
        for role in roles:
            buttons_line.append(Button.inline(
                f"{role.name} (@{role.nickname})",
                DeleteRoleEvent(self._sender, role.id).save_get_id()
            ))
            if len(buttons_line) == 2:
                buttons.append(buttons_line.copy())
                buttons_line = []
        if buttons_line:
            buttons.append(buttons_line.copy())

        buttons.append([Button.inline("<< К меню ролей", GeneralMenuRoleEvent(self._sender).save_get_id())])
        await self._menu_message.edit("Удалить роль:", buttons=buttons)

    async def action_menu(self):
        role = self.query_event.get_role()
        await self._menu_message.edit(f"Меню роли **{role.name}** (@{role.nickname}):", buttons=[
            [
                Button.inline('Участники', ListMembersRoleEvent(self._sender, role.id).save_get_id()),
            ],
            [
                Button.inline('Изменить', ChangeRoleEvent(self._sender, role.id).save_get_id()),
                Button.inline('Удалить', DeleteRoleEvent(self._sender, role.id).save_get_id()),
            ],
            [
                Button.inline('<< К списку ролей', ListRoleEvent(self._sender).save_get_id())
            ],
        ])

    async def action_delete(self):
        role = self.query_event.get_role()
        role.delete_instance()
        await self._client.send_message(self.entity, f"Удалена роль: {role.name} (@{role.nickname})")
        await self.action_list(True)

    async def action_change(self):
        role = self.query_event.get_role()

        async with self._client._client.conversation(self.entity) as conv:
            try:
                params = await self.get_role_params(conv)
                if params:
                    old_name = role.name
                    old_nickname = role.nickname
                    role.name = params[0]
                    role.nickname = params[1]
                    role.save()
                    await conv.send_message(f"Изменена роль: {old_name} (@{old_nickname})")
                else:
                    await conv.send_message("Такая роль уже существует")
                    return
            except TimeoutError:
                await conv.send_message(ConversationTimeoutError.message)
            except InputValueError as ex:
                await conv.send_message(ex.message)

        await self._client._client.send_message(entity=self.entity, message=self._menu_message)

    async def get_role_members(self, role: Role) -> list:
        actual_members = await self._client.get_dialog_members(self.entity)
        db_members = {}
        for role_member in MemberRole.select().where(MemberRole.role == role):
            db_members[role_member.member.user.telegram_id] = role_member.member

        result = []
        for tg_member in actual_members:
            if tg_member.id in db_members:
                result.append((tg_member, db_members[tg_member.id]))
        return result

    async def action_list_members(self, new_message: bool = False):
        role = self.query_event.get_role()
        members_names = []
        for tg_member, db_member in await self.get_role_members(role):
            members_names.append(
                f"{tg_member.first_name} {f'(@{tg_member.username})' if tg_member.username else ''}".strip(' ')
            )
        if members_names:
            text = f"**Участники {role.name} (@{role.nickname}):**\n" + '\n'.join(members_names)
        else:
            text = f"У роли {role.name} (@{role.nickname}) нет участников"

        buttons = [
            [
                Button.inline('Добавить участника', AddMemberMenuRoleEvent(self._sender, role.id).save_get_id()),
                Button.inline('Удалить участника', RemoveMemberMenuRoleEvent(self._sender, role.id).save_get_id()),
            ],
            [
                Button.inline('<< К меню роли', MenuRoleEvent(self._sender, role.id).save_get_id())
            ],
        ]
        if new_message:
            await self._client.send_message(self.entity, text, buttons=buttons)
        else:
            await self._menu_message.edit(text, buttons=buttons)

    async def action_add_member_menu(self, new_message: bool = False):
        role = self.query_event.get_role()
        chat = Chat.get(Chat.telegram_id == self.entity.id)

        role_members_tg_ids = [tg_member.id for tg_member, db_member in await self.get_role_members(role)]
        buttons = []
        buttons_line = []
        for tg_member in await self._client.get_dialog_members(self.entity):
            if tg_member.id in role_members_tg_ids:
                continue

            first_name = tg_member.first_name if tg_member.first_name else ''
            last_name = tg_member.last_name if tg_member.last_name else ''
            user = User.get_or_create(
                telegram_id=tg_member.id,
                defaults={
                    'name': f"{first_name} {last_name}".strip(' '),
                    'nickname': tg_member.username
                }
            )[0]
            db_member = Member.get_or_create(chat=chat, user=user)[0]

            buttons_line.append(Button.inline(
                self.get_username_string(tg_member.first_name, tg_member.username),
                AddMemberRoleEvent(sender=self._sender, role_id=role.id, member_id=db_member.id).save_get_id()
            ))
            if len(buttons_line) == 2:
                buttons.append(buttons_line.copy())
                buttons_line = []
        if buttons_line:
            buttons.append(buttons_line.copy())
        buttons.append([Button.inline('<< Участники', ListMembersRoleEvent(self._sender, role.id).save_get_id())])

        text = f"Добавить участника к роли {role.name} (@{role.nickname}):"
        if new_message:
            await self._client.send_message(self.entity, text, buttons=buttons)
        else:
            await self._menu_message.edit(text, buttons=buttons)

    async def action_add_member(self):
        role = self.query_event.get_role()
        member = self.query_event.get_member()

        if MemberRole.get_or_none(MemberRole.role == role, MemberRole.member == member):
            await self._client.send_message(self.entity, f"Этот участник уже добавлен {role.name} (@{role.nickname}).")
            return
        else:
            MemberRole.create(role=role, member=member)
            await self._client.send_message(
                self.entity,
                f"К роли {role.name} (@{role.nickname}) добавлен участник:\n" +
                self.get_username_string(member.user.name, member.user.nickname)
            )

        await self.action_list_members(True)

    async def action_remove_member_menu(self, new_message: bool = False):
        role = self.query_event.get_role()

        buttons = []
        buttons_line = []
        for tg_member, db_member in await self.get_role_members(role):
            buttons_line.append(Button.inline(
                self.get_username_string(tg_member.first_name, tg_member.username),
                RemoveMemberRoleEvent(sender=self._sender, role_id=role.id, member_id=db_member.id).save_get_id()
            ))
            if len(buttons_line) == 2:
                buttons.append(buttons_line.copy())
                buttons_line = []
        if buttons_line:
            buttons.append(buttons_line.copy())
        buttons.append([Button.inline('<< Участники', ListMembersRoleEvent(self._sender, role.id).save_get_id())])

        text = f"Удалить участника из роли {role.name} (@{role.nickname}):"
        if new_message:
            await self._client.send_message(self.entity, text, buttons=buttons)
        else:
            await self._menu_message.edit(text, buttons=buttons)

    async def action_remove_member(self):
        role = self.query_event.get_role()
        member = self.query_event.get_member()
        role_member = MemberRole.get_or_none(MemberRole.role == role, MemberRole.member == member)

        if not role_member:
            await self._client.send_message(self.entity, f"Этот участник уже удален из {role.name} (@{role.nickname}).")
        else:
            role_member.delete_instance()
            await self._client.send_message(
                self.entity,
                f"Из роли {role.name} (@{role.nickname}) удален участник:\n" +
                self.get_username_string(member.user.name, member.user.nickname)
            )

        await self.action_list_members(True)

    @staticmethod
    def get_username_string(name: Union[str, None], nickname: Union[str, None]) -> str:
        name = name if name else ''

        if nickname and not name:
            nickname = '@' + nickname
        elif nickname:
            nickname = f'(@{nickname})'
        else:
            nickname = ''

        return f"{name} {nickname}".strip(' ')

    async def action_truncate(self):
        pass
