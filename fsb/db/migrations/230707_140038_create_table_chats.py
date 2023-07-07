"""
create table chats
date created: 2023-07-07 11:00:38.059042
"""


def upgrade(migrator):
    with migrator.create_table('chats') as table:
        table.primary_key('id')
        table.biginteger('telegram_id', unique=True)
        table.char('name', max_length=255, null=True)
        table.int('type')
        table.text('input_peer', null=True)
        table.bool('dude', constraints=['DEFAULT 0'])


def downgrade(migrator):
    migrator.drop_table('chats')
