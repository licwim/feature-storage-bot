"""
create table ratings_members
date created: 2023-07-07 11:02:14.170941
"""


def upgrade(migrator):
    with migrator.create_table('ratings_members') as table:
        table.primary_key('id')
        table.foreign_key('AUTO', 'member_id', on_delete='CASCADE', on_update=None, references='chats_members.id')
        table.foreign_key('AUTO', 'rating_id', on_delete='CASCADE', on_update=None, references='ratings.id')
        table.int('total_count')
        table.int('month_count')
        table.int('current_month_count')
        table.datetime('created_at', constraints=['DEFAULT CURRENT_TIMESTAMP'])


def downgrade(migrator):
    migrator.drop_table('ratings_members')
