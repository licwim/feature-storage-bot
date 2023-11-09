"""
create table ratings_members
date created: 2023-07-07 11:02:14.170941
"""


def upgrade(migrator):
    with migrator.create_table('ratings_members') as table:
        table.primary_key('id')
        table.foreign_key('AUTO', 'member_id', on_delete='CASCADE', on_update=None, references='chats_members.id')
        table.foreign_key('AUTO', 'rating_id', on_delete='CASCADE', on_update=None, references='ratings.id')
        table.int('total_count', constraints=['DEFAULT 0'])
        table.int('month_count', constraints=['DEFAULT 0'])
        table.int('current_month_count', constraints=['DEFAULT 0'])
        table.datetime('created_at', constraints=['DEFAULT CURRENT_TIMESTAMP'])

    migrator.add_column('ratings', 'last_winner_id', 'int', null=True)
    migrator.add_column('ratings', 'last_month_winner_id', 'int', null=True)
    migrator.add_foreign_key_constraint('ratings', 'last_winner_id', 'ratings_members', 'id', on_delete='SET NULL', on_update=None)
    migrator.add_foreign_key_constraint('ratings', 'last_month_winner_id', 'ratings_members', 'id', on_delete='SET NULL', on_update=None)


def downgrade(migrator):
    migrator.drop_column('ratings', 'last_winner_id')
    migrator.drop_column('ratings', 'last_month_winner_id')
    migrator.drop_table('ratings_members')
