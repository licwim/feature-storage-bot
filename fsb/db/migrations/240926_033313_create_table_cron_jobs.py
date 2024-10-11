"""
create table cron_jobs
date created: 2024-09-26 00:33:13.526815
"""


def upgrade(migrator):
    with migrator.create_table('cron_jobs') as table:
        table.primary_key('id')
        table.char('name', max_length=255)
        table.foreign_key('AUTO', 'chat_id', on_delete='CASCADE', on_update='CASCADE', references='chats.id')
        table.char('message', max_length=255)
        table.char('schedule', max_length=255)
        table.bool('active', constraints=['DEFAULT 1'])
        table.datetime('created_at', constraints=['DEFAULT CURRENT_TIMESTAMP'])
        table.datetime('updated_at', constraints=['DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'])

    sql = """INSERT INTO modules (name, readable_name) VALUES (%s, %s)"""
    params = ('cron', 'Планировщик')
    migrator.execute_sql(sql, params)


def downgrade(migrator):
    migrator.drop_table('cron_jobs')
    migrator.execute_sql("DELETE FROM modules WHERE name = 'cron'")
