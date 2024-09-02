"""
create table chats_modules
date created: 2024-07-28 11:23:01.081758
"""


def upgrade(migrator):
    with migrator.create_table('chats_modules') as table:
        table.foreign_key('AUTO', 'chat_id', on_delete='CASCADE', on_update='CASCADE', references='chats.id')
        table.char('module_id', max_length=255, null=False)
        table.add_constraint('PRIMARY KEY (chat_id, module_id)')

    migrator.add_foreign_key_constraint('chats_modules', 'module_id', 'modules', 'name', on_delete='CASCADE', on_update='CASCADE')


def downgrade(migrator):
    migrator.drop_table('chats_modules')
