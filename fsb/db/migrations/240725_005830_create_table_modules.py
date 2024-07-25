"""
create table modules
date created: 2024-07-24 21:58:30.566136
"""


def upgrade(migrator):
    with migrator.create_table('modules') as table:
        table.foreign_key('AUTO', 'chat_id', on_delete='CASCADE', on_update='CASCADE', references='chats.id')
        table.add_constraint('PRIMARY KEY (chat_id)')
        table.bool('roles', constraints=['DEFAULT 0'])
        table.bool('ratings', constraints=['DEFAULT 0'])
        table.bool('dude', constraints=['DEFAULT 0'])
        table.bool('happy_new_year', constraints=['DEFAULT 0'])
        table.bool('birthday', constraints=['DEFAULT 0'])

    migrator.drop_column('chats', 'dude')
    migrator.drop_column('chats', 'happy_new_year')
    migrator.drop_column('chats', 'birthday')


def downgrade(migrator):
    migrator.drop_table('modules')

    migrator.add_column('chats', 'dude', 'bool', null=False, default=0)
    migrator.add_column('chats', 'happy_new_year', 'bool', null=False, default=0)
    migrator.add_column('chats', 'birthday', 'bool', null=False, default=0)
