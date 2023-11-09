"""
create table users
date created: 2023-07-07 11:00:32.133262
"""


def upgrade(migrator):
    with migrator.create_table('users') as table:
        table.primary_key('id')
        table.biginteger('telegram_id', unique=True)
        table.char('name', max_length=255, null=True)
        table.char('nickname', max_length=255, null=True)
        table.char('phone', max_length=255, null=True)
        table.text('input_peer', null=True)


def downgrade(migrator):
    migrator.drop_table('users')
