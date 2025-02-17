# !/usr/bin/env python

import os
from datetime import datetime
from zoneinfo import ZoneInfo

from peewee import SQL, Model
from peewee_async import PooledMySQLDatabase
from peewee_moves import DatabaseManager as BaseDatabaseManager, Migrator as BaseMigrator, LOGGER
from playhouse.shortcuts import ReconnectMixin

from fsb.config import config

MAX_DB_CONNECTIONS = 10


class ReconnectedPooledDatabase(ReconnectMixin, PooledMySQLDatabase):
    pass


class Migrator(BaseMigrator):
    def add_foreign_key_constraint(self, table, column_name, rel, rel_column,
                                   on_delete=None, on_update=None):
        self.migrator.add_foreign_key_constraint(table, column_name, rel, rel_column,
                                                 on_delete=on_delete, on_update=on_update).run()

    def drop_foreign_key_constraint(self, table, column_name):
        self.migrator.drop_foreign_key_constraint(table, column_name).run()

    def add_column(self, table, name, coltype, null=True, default=None, constraints=None, safe=True, **kwargs):
        # peewee-moves некорректно обрабатывает NOT NULL, поэтому этот параметр надо указывать в constraints
        extended_constraints = []

        if constraints:
            if isinstance(constraints, list):
                for constraint in constraints:
                    extended_constraints.append(SQL(constraint))
            elif isinstance(constraints, str):
                extended_constraints.append(SQL(constraints))

        if null == False:
            extended_constraints.insert(0, SQL('NOT NULL'))

        if default != None:
            extended_constraints.insert(0, SQL(f'DEFAULT {default}'))

        extended_constraints = extended_constraints if extended_constraints else None

        columns = [column.name for column in self.database.get_columns(table)]

        if not safe or name not in columns:
            super().add_column(table, name, coltype, null=True, default=default, constraints=extended_constraints, **kwargs)

    def drop_column(self, table, name, safe=True, **kwargs):
        columns = [column.name for column in self.database.get_columns(table)]

        if not safe or name in columns:
            super().drop_column(table, name, **kwargs)


class DatabaseManager(BaseDatabaseManager):
    def __init__(self, database, table_name=None, directory='migrations'):
        super().__init__(database=database, table_name=table_name, directory=directory)
        self.migrator = Migrator(self.database)

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


database = ReconnectedPooledDatabase(
    database=config.DB_NAME,
    user=config.DB_USER,
    password=config.str('DB_PASSWORD'),
    host=config.DB_HOST,
    port=3306,
    max_connections=MAX_DB_CONNECTIONS,
    charset='utf8mb4'
)

db_manager = DatabaseManager(
    database,
    directory=os.path.abspath(config.ROOT_FOLDER + '/fsb/db/migrations'),
    table_name='migrations'
)


class ModelInterface(Model):
    pass
