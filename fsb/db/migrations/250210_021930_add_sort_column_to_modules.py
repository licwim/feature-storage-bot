"""
add_sort_column_to_modules
date created: 2025-02-09 23:19:30.798676
"""

from fsb.db.models import Module


def upgrade(migrator):
    migrator.add_column('modules', 'sort', 'int', null=False)

    s = 1
    sql_values = []
    params = ()

    for module_name in Module.MODULES_LIST:
        sql_values.append('(%s, %s)')
        params += (module_name, s)
        s += 1

    sql = ("""
    INSERT INTO modules (name, sort)
     VALUES {sql_values} as new
     ON DUPLICATE KEY UPDATE sort = new.sort;
      """).format(sql_values=', '.join(sql_values))

    migrator.execute_sql(sql, params)


def downgrade(migrator):
    migrator.drop_column('modules', 'sort')
