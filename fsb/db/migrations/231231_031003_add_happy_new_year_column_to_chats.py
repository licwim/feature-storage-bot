"""
add_happy_new_year_column_to_chats
date created: 2023-12-31 00:10:03.022653
"""


def upgrade(migrator):
    migrator.add_column('chats', 'happy_new_year', 'bool', null=False, default=0)


def downgrade(migrator):
    migrator.drop_column('chats', 'happy_new_year')
