# !/usr/bin/env python

from asyncio.exceptions import TimeoutError

from inflection import underscore
from telethon import events
from telethon.tl.custom.button import Button

from fsb.db.models import Chat
from fsb.db.models import Member
from fsb.db.models import MemberRole
from fsb.db.models import Role
from fsb.db.models import User
from fsb.error import ConversationTimeoutError
from fsb.error import InputValueError
from fsb.events.roles import (
    RoleQueryEvent, GeneralMenuRoleEvent, ListRoleEvent, MenuRoleEvent, DeleteRoleEvent,
    ChangeRoleEvent, ListMembersRoleEvent, AddMemberMenuRoleEvent, AddMemberRoleEvent, RemoveMemberMenuRoleEvent,
    RemoveMemberRoleEvent
)
from fsb.handlers import CommandHandler, MenuHandler
from fsb.helpers import Helper


class RolesSettingsCommandHandler(CommandHandler):
    async def run(self):
        await super().run()
        text, buttons = GeneralMenuRoleEvent.get_message_and_buttons(self.sender.id)
        await self.client.send_message(self.chat, text, buttons=buttons)


class RolesSettingsQueryHandler(MenuHandler):
    async def run(self):
        await super().run()
        if not isinstance(self.query_event, RoleQueryEvent):
            return

        query_event_type = underscore(self.query_event.__class__.__name__.replace('RoleEvent', ''))
        action = getattr(self, 'action_' + query_event_type)
        if action:
            await action()

    async def action_general_menu(self):
        text, buttons = GeneralMenuRoleEvent.get_message_and_buttons(self.sender.id)
        await self.menu_message.edit(text, buttons=buttons)

    async def get_role_params(self, conv):
        response = conv.wait_event(
            events.NewMessage(forwards=False, chats=self.chat, from_users=self.sender.id),
            timeout=self.INPUT_TIMEOUT
        )
        await conv.send_message('Введи тег роли либо название и тег через запятую\n(Rolename, roletag)')
        response_event = await response

        name, nickname = Role.parse_from_message(response_event.message.text)

        chat = Chat.get_or_create(
            telegram_id=self.chat.id,
            defaults={
                'name': self.chat.title,
                'type': Chat.get_chat_type(self.chat)
            }
        )[0]

        if Role.get_or_none(Role.chat == chat, Role.nickname == nickname):
            return None
        else:
            return name, nickname, chat

    async def action_create(self):
        async with self.client._client.conversation(self.chat) as conv:
            try:
                params = await self.get_role_params(conv)
                if params:
                    Role.create(name=params[0], nickname=params[1], chat=params[2]).save()
                    await conv.send_message(f"Создана роль: {params[0]} (__{params[1]}__)")
                else:
                    await conv.send_message("Такая роль уже существует")
                    return
            except TimeoutError:
                await conv.send_message(ConversationTimeoutError.message)
            except InputValueError as ex:
                await conv.send_message(ex.message)

        await self.client._client.send_message(entity=self.chat, message=self.menu_message)

    async def action_list(self, new_message: bool = False):
        chat = Chat.get_or_create(
            telegram_id=self.chat.id,
            defaults={
                'name': self.chat.title,
                'type': Chat.get_chat_type(self.chat)
            }
        )[0]
        roles = Role.find_by_chat(chat)
        buttons = []
        buttons_line = []
        for role in roles:
            buttons_line.append(Button.inline(
                f"{role.name} (@{role.nickname})",
                MenuRoleEvent(self.sender.id, role.id).save_get_id()
            ))
            if len(buttons_line) == 2:
                buttons.append(buttons_line.copy())
                buttons_line = []
        if buttons_line:
            buttons.append(buttons_line.copy())
        buttons.append([Button.inline("<< К меню ролей", GeneralMenuRoleEvent(self.sender.id).save_get_id())])
        text = "Список ролей:"
        if new_message:
            await self.client.send_message(self.chat, text, buttons=buttons)
        else:
            await self.menu_message.edit(text, buttons=buttons)

    async def action_delete_menu(self):
        chat = Chat.get_or_create(
            telegram_id=self.chat.id,
            defaults={
                'name': self.chat.title,
                'type': Chat.get_chat_type(self.chat)
            }
        )[0]
        roles = Role.find_by_chat(chat)
        buttons = []
        buttons_line = []
        for role in roles:
            buttons_line.append(Button.inline(
                f"{role.name} (@{role.nickname})",
                DeleteRoleEvent(self.sender.id, role.id).save_get_id()
            ))
            if len(buttons_line) == 2:
                buttons.append(buttons_line.copy())
                buttons_line = []
        if buttons_line:
            buttons.append(buttons_line.copy())

        buttons.append([Button.inline("<< К меню ролей", GeneralMenuRoleEvent(self.sender.id).save_get_id())])
        await self.menu_message.edit("Удалить роль:", buttons=buttons)

    async def action_menu(self, new_message: bool = False):
        role = self.query_event.get_role()
        text = f"Меню роли **{role.name}** (@{role.nickname}):"
        buttons = [
            [
                Button.inline('Участники', ListMembersRoleEvent(self.sender.id, role.id).save_get_id()),
            ],
            [
                Button.inline('Изменить', ChangeRoleEvent(self.sender.id, role.id).save_get_id()),
                Button.inline('Удалить', DeleteRoleEvent(self.sender.id, role.id).save_get_id()),
            ],
            [
                Button.inline('<< К списку ролей', ListRoleEvent(self.sender.id).save_get_id())
            ],
        ]

        if new_message:
            await self.client.send_message(self.chat, text, buttons=buttons)
        else:
            await self.menu_message.edit(text, buttons=buttons)

    async def action_delete(self):
        role = self.query_event.get_role()
        role.delete_instance()
        await self.client.send_message(self.chat, f"Удалена роль: {role.name} (__{role.nickname}__)")
        await self.action_list(True)

    async def action_change(self):
        role = self.query_event.get_role()

        async with self.client._client.conversation(self.chat) as conv:
            try:
                params = await self.get_role_params(conv)
                if params:
                    old_name = role.name
                    old_nickname = role.nickname
                    role.name = params[0]
                    role.nickname = params[1]
                    role.save()
                    await conv.send_message(
                        f"Изменена роль с {old_name} (__{old_nickname}__) на {role.name} (__{role.nickname}__)"
                    )
                else:
                    await conv.send_message("Такая роль уже существует")
                    return
            except TimeoutError:
                await conv.send_message(ConversationTimeoutError.message)
            except InputValueError as ex:
                await conv.send_message(ex.message)

        await self.action_menu(True)

    async def get_role_members(self, role: Role) -> list:
        return Helper.collect_members(
            await self.client.get_dialog_members(self.chat),
            MemberRole.select().where(MemberRole.role == role)
        )

    async def action_list_members(self, new_message: bool = False):
        role = self.query_event.get_role()
        members_names = []
        for tg_member, db_member in await self.get_role_members(role):
            members_names.append(Helper.make_member_name(tg_member))
        if members_names:
            text = f"**Участники {role.name} (__{role.nickname}__):**\n" + '\n'.join(members_names)
        else:
            text = f"У роли {role.name} (__{role.nickname}__) нет участников"

        buttons = [
            [
                Button.inline('Добавить участника', AddMemberMenuRoleEvent(self.sender.id, role.id).save_get_id()),
                Button.inline('Удалить участника', RemoveMemberMenuRoleEvent(self.sender.id, role.id).save_get_id()),
            ],
            [
                Button.inline('<< К меню роли', MenuRoleEvent(self.sender.id, role.id).save_get_id())
            ],
        ]
        if new_message:
            await self.client.send_message(self.chat, text, buttons=buttons)
        else:
            await self.menu_message.edit(text, buttons=buttons)

    async def action_add_member_menu(self, new_message: bool = False):
        role = self.query_event.get_role()
        chat = Chat.get_by_telegram_id(self.chat.id)

        role_members_tg_ids = [tg_member.id for tg_member, db_member in await self.get_role_members(role)]
        members = []
        for tg_member in await self.client.get_dialog_members(self.chat):
            if tg_member.id in role_members_tg_ids:
                continue

            user = User.get_or_create(
                telegram_id=tg_member.id,
                defaults={
                    'name': Helper.make_member_name(tg_member, with_username=False),
                    'nickname': tg_member.username
                }
            )[0]
            db_member = Member.get_or_create(chat=chat, user=user)[0]

            members.append((tg_member, db_member))

        await self._member_menu('add', members, new_message)

    async def action_add_member(self):
        role = self.query_event.get_role()
        member = self.query_event.get_member()

        if MemberRole.get_or_none(MemberRole.role == role, MemberRole.member == member):
            await self.client.send_message(self.chat, f"Этот участник уже добавлен к {role.name} (__{role.nickname}__).")
            return
        else:
            MemberRole.create(role=role, member=member)
            await self.action_add_member_menu()

    async def action_remove_member_menu(self, new_message: bool = False):
        role = self.query_event.get_role()
        members = [(tg_member, db_member.member) for tg_member, db_member in await self.get_role_members(role)]
        await self._member_menu('remove', members, new_message)

    async def action_remove_member(self):
        role = self.query_event.get_role()
        member = self.query_event.get_member()
        role_member = MemberRole.get_or_none(MemberRole.role == role, MemberRole.member == member)

        if not role_member:
            await self.client.send_message(self.chat, f"Этот участник уже удален из {role.name} (@{role.nickname}).")
        else:
            role_member.delete_instance()
            await self.action_remove_member_menu()

    async def _member_menu(self, action: str, members: list, new_message: bool = False):
        role = self.query_event.get_role()

        match action:
            case 'add':
                event_class = AddMemberRoleEvent
                text = f"Добавить участника к роли {role.name} (__{role.nickname}__):"
            case 'remove':
                event_class = RemoveMemberRoleEvent
                text = f"Удалить участника из роли {role.name} (__{role.nickname}__):"
            case _:
                raise ValueError

        buttons = []
        for tg_member, db_member in members:
            buttons.append((
                Helper.make_member_name(tg_member, with_mention=True),
                event_class(sender_id=self.sender.id, role_id=role.id, member_id=db_member.id).save_get_id()
            ))
        buttons = Helper.make_buttons_layout(
            buttons,
            ("<< Участники", ListMembersRoleEvent(self.sender.id, role.id).save_get_id())
        )

        if new_message:
            await self.client.send_message(self.chat, text, buttons=buttons)
        else:
            await self.menu_message.edit(text, buttons=buttons)

    async def action_truncate(self):
        pass
