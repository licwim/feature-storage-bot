"""
create table chats_members_roles
date created: 2023-07-07 11:01:56.518428
"""


def upgrade(migrator):
    with migrator.create_table('chats_members_roles') as table:
        table.foreign_key('AUTO', 'member_id', on_delete=None, on_update=None, references='chats_members.id')
        table.foreign_key('AUTO', 'role_id', on_delete='CASCADE', on_update=None, references='roles.id')


def downgrade(migrator):
    migrator.drop_table('chats_members_roles')
