# !/usr/bin/env python

import re

from peewee import DoesNotExist

from fsb.db.models import Chat, MemberRole, Role
from fsb.handlers import WatcherHandler


class MentionWatcherHandler(WatcherHandler):
    UNKNOWN_NAME_REPLACEMENT = "ты"

    async def run(self):
        members = await self.client.get_dialog_members(self.chat)
        members.remove(self.sender)
        mentions = [matches[1] for matches in re.findall(r"(\s+|^)@([^\s@]+)", self.message.text)]

        mentions_strings = []
        for mention in mentions:
            mention_string, added_members = self._resolve_mention(mention, members)
            if mention_string:
                mentions_strings.append(mention_string)

            for member in added_members:
                members.remove(member)

        if mentions_strings:
            await self.client.send_message(
                self.chat,
                ' '.join(mentions_strings),
                self.message
            )

    def _make_mention_string(self, members: list, rank_mention: bool = False):
        result_mentions = []
        for member in members:
            rank = None
            if rank_mention:
                try:
                    rank = member.participant.rank
                except AttributeError:
                    pass
            if rank:
                result_mentions.append(f"[{rank}](tg://user?id={str(member.id)})")
            elif member.username:
                result_mentions.append('@' + member.username)
            else:
                member_name = member.first_name if member.first_name else self.UNKNOWN_NAME_REPLACEMENT
                result_mentions.append(f"[{member_name}](tg://user?id={str(member.id)})")

        return ' '.join(result_mentions)

    def _resolve_mention(self, mention: str, members: list) -> tuple:
        match mention:
            case 'all':
                rank = False
            case 'allrank':
                rank = True
            case _:
                return self._resolve_custom_mention(mention, members)

        return self._make_mention_string(members, rank), members

    def _resolve_custom_mention(self, mention: str, original_members: list) -> tuple:
        try:
            role_members = MemberRole.select().where(
                MemberRole.role == Role.get(
                    Role.chat == Chat.get(Chat.telegram_id == self.chat.id).get_id(),
                    Role.nickname == mention
                )
            )

            members_ids = [role_member.member.user.telegram_id for role_member in role_members]
            members = [member for member in original_members if member.id in members_ids]
        except DoesNotExist:
            return None, []

        return self._make_mention_string(members, False), members

