# !/usr/bin/env python

from collections import OrderedDict

from peewee import DoesNotExist

from fsb.db.models import Chat, MemberRole, Role
from fsb.handlers import MentionHandler


class AllMentionHandler(MentionHandler):
    async def run(self):
        await super().run()
        members = await self.client.get_dialog_members(self.chat)
        members.remove(self.sender)
        return self.get_members_mentions(members, 'allrank' in self.mentions)


class CustomMentionHandler(MentionHandler):
    async def run(self):
        await super().run()
        members = await self.client.get_dialog_members(self.chat)
        members.remove(self.sender)
        members_mentions = []

        for role in Role.find_by_chat(Chat.get_by_telegram_id(self.chat.id)):
            if role.nickname in self.mentions:
                members_mentions += self.get_members_mentions_by_role(members, role)

        return list(OrderedDict.fromkeys(members_mentions))

    def get_members_mentions_by_role(self, all_members: list, role: Role) -> list:
        try:
            role_members = MemberRole.select().where(MemberRole.role == role)
            members_ids = [role_member.member.user.telegram_id for role_member in role_members]
            members = [member for member in all_members if member.id in members_ids]
            return self.get_members_mentions(members)
        except DoesNotExist:
            return []
