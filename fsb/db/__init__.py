# !/usr/bin/env python

import os
from datetime import datetime
from zoneinfo import ZoneInfo

from peewee_async import PooledMySQLDatabase
from peewee_moves import DatabaseManager as BaseDatabaseManager, LOGGER
from playhouse.migrate import MySQLMigrator
from playhouse.shortcuts import ReconnectMixin

from fsb.config import config

MAX_DB_CONNECTIONS = 10


class ReconnectedPooledDatabase(ReconnectMixin, PooledMySQLDatabase):
    pass


class DatabaseManager(BaseDatabaseManager):
    def get_ident(self):
        return datetime.now(ZoneInfo(config.TZ)).strftime('%y%m%d_%H%M%S')

    def upgrade(self, count=None, fake=False):
        if count < 0:
            return False

        diff = self.diff if not count else self.diff[:count]

        if not diff:
            LOGGER.info('all migrations applied!')
            return True

        for name in diff:
            success = self.run_migration(name, 'upgrade', fake=fake)

            if not success:
                return False
        return True

    def downgrade(self, count=1, fake=False):
        if count < 1:
            return False

        diff = self.db_migrations[:-1 * (count + 1):-1]

        if not diff:
            LOGGER.info('migrations not yet applied!')
            return False

        for name in diff:
            success = self.run_migration(name, 'downgrade', fake=fake)

            if not success:
                return False
        return True


base_db = ReconnectedPooledDatabase(
    database=config.DB_NAME,
    user=config.DB_USER,
    password=config.str('DB_PASSWORD'),
    host=config.DB_HOST,
    port=3306,
    max_connections=MAX_DB_CONNECTIONS,
    charset='utf8mb4'
)

base_migrator = MySQLMigrator(base_db)
db_manager = DatabaseManager(
    base_db,
    directory=os.path.abspath(config.ROOT_FOLDER + '/fsb/db/migrations'),
    table_name='migrations'
)
