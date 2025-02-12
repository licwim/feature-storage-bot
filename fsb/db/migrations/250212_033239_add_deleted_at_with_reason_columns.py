"""
add_deleted_at_with_reason_columns
date created: 2025-02-12 00:32:39.946905
"""

from datetime import datetime


def upgrade(migrator):
    migrator.add_column('users', 'deleted_at', 'datetime')
    migrator.add_column('users', 'deletion_reason', 'text')

    migrator.add_column('chats', 'deleted_at', 'datetime')
    migrator.add_column('chats', 'deletion_reason', 'text')

    migrator.add_column('chats_members', 'deleted_at', 'datetime')
    migrator.add_column('chats_members', 'deletion_reason', 'text')

    sql = """
    UPDATE chats_members SET deleted_at = %s WHERE active = %s;
    """

    migrator.execute_sql(sql, (datetime.now(), 0))

    migrator.drop_column('chats_members', 'active')


def downgrade(migrator):
    migrator.drop_column('users', 'deleted_at')
    migrator.drop_column('users', 'deletion_reason')

    migrator.drop_column('chats', 'deleted_at')
    migrator.drop_column('chats', 'deletion_reason')

    migrator.add_column('chats_members', 'active', 'bool', null=False, default=1)

    sql = """
    UPDATE chats_members SET active = 0 WHERE deleted_at IS NOT NULL;
    """

    migrator.execute_sql(sql)

    migrator.drop_column('chats_members', 'deleted_at')
    migrator.drop_column('chats_members', 'deletion_reason')
