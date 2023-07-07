"""
create table ratings
date created: 2023-07-07 11:02:06.547449
"""


def upgrade(migrator):
    with migrator.create_table('ratings') as table:
        table.primary_key('id')
        table.char('name', max_length=255)
        table.foreign_key('AUTO', 'chat_id', on_delete=None, on_update=None, references='chats.id')
        table.char('command', max_length=255)
        table.datetime('last_run', null=True)
        table.datetime('last_month_run', null=True)
        table.bool('autorun', constraints=['DEFAULT 0'])
        table.foreign_key('AUTO', 'last_winner_id', null=True, on_delete='SET NULL', on_update=None, references='ratings_members.id')
        table.foreign_key('AUTO', 'last_month_winner_id', null=True, on_delete='SET NULL', on_update=None, references='ratings_members.id')


def downgrade(migrator):
    migrator.drop_table('ratings')
