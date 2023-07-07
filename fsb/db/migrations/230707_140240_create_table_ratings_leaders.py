"""
create table ratings_leaders
date created: 2023-07-07 11:02:40.518331
"""


def upgrade(migrator):
    with migrator.create_table('ratings_leaders') as table:
        table.primary_key('id')
        table.foreign_key('AUTO', 'rating_member_id', on_delete='CASCADE', on_update='CASCADE', references='ratings_members.id')
        table.date('date')
        table.foreign_key('AUTO', 'chat_id', on_delete='CASCADE', on_update='CASCADE', references='chats.id')


def downgrade(migrator):
    migrator.drop_table('ratings_leaders')
