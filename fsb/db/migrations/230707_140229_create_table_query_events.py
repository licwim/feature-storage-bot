"""
create table query_events
date created: 2023-07-07 11:02:29.770211
"""


def upgrade(migrator):
    with migrator.create_table('query_events') as table:
        table.primary_key('id')
        table.char('module_name', constraints=['DEFAULT "module"'], max_length=255, null=True)
        table.char('class_name', constraints=['DEFAULT "class"'], max_length=255, null=True)
        table.text('data', null=True)
        table.datetime('created_at', constraints=['DEFAULT CURRENT_TIMESTAMP'])


def downgrade(migrator):
    migrator.drop_table('query_events')
