"""
create table roles
date created: 2023-07-07 11:00:53.745253
"""


def upgrade(migrator):
    with migrator.create_table('roles') as table:
        table.primary_key('id')
        table.char('name', max_length=255, null=True)
        table.char('nickname', max_length=255, null=True)
        table.foreign_key('AUTO', 'chat_id', on_delete=None, on_update=None, references='chats.id')


def downgrade(migrator):
    migrator.drop_table('roles')
