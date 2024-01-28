"""
create table cache_quantum_rand
date created: 2023-07-07 11:02:47.711145
"""


def upgrade(migrator):
    with migrator.create_table('cache_quantum_rand') as table:
        table.primary_key('id')
        table.int('value')
        table.char('type', constraints=['DEFAULT "uint16"'], max_length=255)


def downgrade(migrator):
    migrator.drop_table('cache_quantum_rand')
