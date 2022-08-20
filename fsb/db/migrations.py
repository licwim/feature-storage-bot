# !/usr/bin/env python

from playhouse.migrate import migrate

from fsb import logger
from fsb.db import base_migrator
from fsb.db.models import Chat
from fsb.db.models import Member
from fsb.db.models import MemberRole
from fsb.db.models import QueryEvent
from fsb.db.models import Rating
from fsb.db.models import RatingMember
from fsb.db.models import Role
from fsb.db.models import User


class BaseMigration:
    __MIGRATION_TABLE_NAME = 'migrations'

    def __init__(self):
        self.db = base_migrator.database

        if not self.db.table_exists(self.__MIGRATION_TABLE_NAME):
            self.db.execute_sql(f'CREATE TABLE {self.__MIGRATION_TABLE_NAME} ('
                                f'  id INT PRIMARY KEY,'
                                f'  migration_name VARCHAR(255) NOT NULL ,'
                                f'  apply_time TIMESTAMP DEFAULT NULL'
                                f')')

    def up(self):
        logger.info(f"Migrate {self.__class__.__name__} ...")

    def down(self):
        logger.info(f"Rollback {self.__class__.__name__} ...")

    @staticmethod
    def migrate_decorator(callback: callable):
        def migration(self):
            migrate(callback(self))
        return migration


class CreatingTables(BaseMigration):
    _tables = []

    def up(self):
        super().up()
        for table in self._tables:
            if table.table_exists():
                raise RuntimeError(f"Table `{table.TABLE_NAME}` already exist")

        self.db.create_tables(self._tables)
        logger.info("Creating tables is done")

    def down(self):
        super().down()
        tables = self._tables.copy()

        for table in self._tables:
            if not table.table_exists():
                tables.remove(table)
        if not tables:
            raise RuntimeError("All tables already dropped")

        self.db.drop_tables(tables)
        logger.info(f"Dropped tables: {', '.join([table.TABLE_NAME for table in tables])}")


class CreateMainTablesMigration(CreatingTables):
    _tables = [
        User,
        Chat,
        Member,
    ]


class CreateRolesTablesMigration(CreatingTables):
    _tables = [
        Role,
        MemberRole,
    ]


class CreateEventsTableMigration(CreatingTables):
    _tables = [
        QueryEvent,
    ]


class CreateTablesForRatingsMigration(CreatingTables):
    _tables = [
        Rating,
        RatingMember,
    ]
