"""
add_created_updated_at_columns
date created: 2025-02-09 21:42:40.648438
"""

_created_at_tables = [
    'users',
    'chats',
    'chats_members',
    'roles',
    'chats_members_roles',
    'ratings',
    'ratings_leaders',
    'chats_modules',
    'query_events',
]

_updated_at_tables = [
    'users',
    'chats',
    'chats_members',
    'roles',
    'chats_members_roles',
    'ratings',
    'ratings_members',
]


def upgrade(migrator):
    for table in _created_at_tables:
        migrator.add_column(table, 'created_at', 'datetime', default='CURRENT_TIMESTAMP')

    for table in _updated_at_tables:
        migrator.add_column(table, 'updated_at', 'datetime', default='CURRENT_TIMESTAMP',
                            constraints=['ON UPDATE CURRENT_TIMESTAMP'])

    migrator.add_column('query_events', 'last_usage_date', 'datetime')

    migrator.drop_column('modules', 'created_at')
    migrator.drop_column('modules', 'updated_at')


def downgrade(migrator):
    for table in _created_at_tables:
        migrator.drop_column(table, 'created_at')

    for table in _updated_at_tables:
        migrator.drop_column(table, 'updated_at')

    migrator.drop_column('query_events', 'last_usage_date')

    migrator.add_column('modules', 'created_at', 'datetime', default='CURRENT_TIMESTAMP')
    migrator.add_column('modules', 'updated_at', 'datetime', default='CURRENT_TIMESTAMP',
                        constraints=['ON UPDATE CURRENT_TIMESTAMP'])
