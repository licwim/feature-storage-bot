# !/usr/bin/env python

from fsb import logger
from fsb.db import base_migrator
from fsb.db.models import Chat
from fsb.db.models import Member
from fsb.db.models import MemberRole
from fsb.db.models import Rating
from fsb.db.models import RatingMember
from fsb.db.models import Role
from fsb.db.models import User


class BaseMigration:
    def up(self):
        logger.info(f"Migrate {self.__class__.__name__} ...")

    def down(self):
        logger.info(f"Rollback {self.__class__.__name__} ...")


class CreateMainTables(BaseMigration):
    _tables = [
        User,
        Chat,
        Member,
        Role,
        MemberRole,
        Rating,
        RatingMember,
    ]

    def up(self):
        super().up()
        for table in self._tables:
            if table.table_exists():
                raise RuntimeError(f"Table `{table.TABLE_NAME}` already exist")

        base_migrator.database.create_tables(self._tables)
        logger.info("Creating tables is done")

    def down(self):
        super().down()
        tables = self._tables.copy()

        for table in self._tables:
            if not table.table_exists():
                tables.remove(table)
        if not tables:
            raise RuntimeError("All tables already dropped")

        base_migrator.database.drop_tables(tables)
        logger.info(f"Dropped tables: {', '.join([table.TABLE_NAME for table in tables])}")
