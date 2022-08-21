# !/usr/bin/env python

from peewee import (
    IntegerField,
    CharField,
    BooleanField,
    TimestampField,
)

from fsb import logger
from fsb.db import base_migrator
from fsb.db.models import (
    BaseModel,
    Chat,
    Member,
    MemberRole,
    QueryEvent,
    Rating,
    RatingMember,
    Role,
    User,
)


class Migration(BaseModel):
    TABLE_NAME = 'migrations'
    position = 0

    id = IntegerField(primary_key=True)
    migration_name = CharField(null=False, unique=True)
    apply = BooleanField(default=False)
    updated_at = TimestampField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = base_migrator.database

    def is_applied(self):
        return self.apply == 1

    def up(self):
        logger.info(f"Migrate {self.__class__.__name__} ...")

    def down(self):
        logger.info(f"Rollback {self.__class__.__name__} ...")

    @staticmethod
    def migrate_decorator(callback: callable):
        def up(self):
            migration = Migration.get_or_none(Migration.migration_name == self.__class__.__name__)
            if migration and migration.is_applied():
                logger.info("Migration already applied")
                return
            callback(self)
            Migration \
                .insert(id=self.position, migration_name=self.__class__.__name__, apply=1) \
                .on_conflict(update={Migration.apply: 1}) \
                .execute()
        return up

    @staticmethod
    def rollback_decorator(callback: callable):
        def down(self):
            migration = Migration.get_or_none(Migration.migration_name == self.__class__.__name__)
            if not migration or not migration.is_applied():
                logger.info("Migration not applied")
                return
            callback(self)
            migration.apply = False
            migration.save()
        return down


class CreatingTables(Migration):
    _tables = []

    @Migration.migrate_decorator
    def up(self):
        super().up()
        for table in self._tables:
            if table.table_exists():
                raise RuntimeError(f"Table `{table.TABLE_NAME}` already exist")

        self.db.create_tables(self._tables)
        logger.info("Creating tables is done")

    @Migration.rollback_decorator
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
