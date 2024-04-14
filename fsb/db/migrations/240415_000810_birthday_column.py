"""
birthday_column
date created: 2024-04-14 21:08:10.798586
"""


def upgrade(migrator):
    migrator.add_column('chats', 'birthday', 'bool', null=False, default=0)
    migrator.add_column('users', 'birthday', 'date', null=True)


def downgrade(migrator):
    migrator.drop_column('chats', 'birthday')
    migrator.drop_column('users', 'birthday')
