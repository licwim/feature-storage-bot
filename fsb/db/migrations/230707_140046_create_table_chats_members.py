"""
create table chats_members
date created: 2023-07-07 11:00:46.093459
"""


def upgrade(migrator):
    with migrator.create_table('chats_members') as table:
        table.primary_key('id')
        table.foreign_key('AUTO', 'chat_id', on_delete=None, on_update=None, references='chats.id')
        table.foreign_key('AUTO', 'user_id', on_delete=None, on_update=None, references='users.id')
        table.char('rang', max_length=255, null=True)


def downgrade(migrator):
    migrator.drop_table('chats_members')
