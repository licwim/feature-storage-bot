"""
create table modules
date created: 2024-07-28 11:19:13.874145
"""


def upgrade(migrator):
    with migrator.create_table('modules') as table:
        table.char('name', max_length=255, constraints=['PRIMARY KEY'])
        table.char('readable_name', max_length=255, null=True)
        table.bool('active', null=False, constraints=['DEFAULT 1'])
        table.datetime('created_at', constraints=['DEFAULT CURRENT_TIMESTAMP'])
        table.datetime('updated_at', constraints=['DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'])

    migrator.drop_column('chats', 'dude')
    migrator.drop_column('chats', 'happy_new_year')
    migrator.drop_column('chats', 'birthday')


def downgrade(migrator):
    migrator.drop_table('modules')

    migrator.add_column('chats', 'dude', 'bool', null=False, default=0)
    migrator.add_column('chats', 'happy_new_year', 'bool', null=False, default=0)
    migrator.add_column('chats', 'birthday', 'bool', null=False, default=0)
