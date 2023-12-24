"""
add_current_year_count_column_for_ratings_members
date created: 2023-12-23 00:51:32.080027
"""

TABLE = 'ratings_members'
COLUMN = 'current_year_count'


def upgrade(migrator):
    migrator.add_column(TABLE, COLUMN, 'int', null=False, default=0, constraints='AFTER current_month_count')


def downgrade(migrator):
    migrator.drop_column(TABLE, COLUMN)
