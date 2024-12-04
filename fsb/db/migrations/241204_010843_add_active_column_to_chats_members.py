"""
add_active_column_to_chats_members
date created: 2024-12-03 22:08:43.381307
"""


def upgrade(migrator):
    migrator.add_column('chats_members', 'active', 'bool', null=False, default=1)


def downgrade(migrator):
    migrator.drop_column('chats_members', 'active')
