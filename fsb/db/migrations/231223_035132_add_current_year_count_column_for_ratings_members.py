"""
add_current_year_count_column_for_ratings_members
date created: 2023-12-23 00:51:32.080027
"""


def upgrade(migrator):
    migrator.add_column('ratings_members', 'current_year_count', 'int', null=False, default=0, constraints='AFTER current_month_count')
    migrator.add_column('ratings', 'last_year_run', 'datetime', null=True, constraints='AFTER last_month_run')
    migrator.add_column('ratings', 'last_year_winner_id', 'int', null=True, constraints='AFTER last_month_winner_id')
    migrator.add_foreign_key_constraint('ratings', 'last_year_winner_id', 'ratings_members', 'id', on_delete='SET NULL', on_update=None)


def downgrade(migrator):
    migrator.drop_foreign_key_constraint('ratings', 'last_year_winner_id')
    migrator.drop_column('ratings_members', 'current_year_count')
    migrator.drop_column('ratings', 'last_year_run')
    migrator.drop_column('ratings', 'last_year_winner_id')
