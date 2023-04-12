# !/usr/bin/env python

from peewee import (
    IntegerField,
    CharField,
    BooleanField,
    TimestampField,
    SQL,
    DateTimeField,
    TextField,
)
from playhouse.migrate import migrate
from playhouse.reflection import Introspector

from fsb import logger
from fsb.db import base_migrator as migrator
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
    RatingLeader,
    CacheQuantumRand,
)
from fsb.telegram.client import TelegramApiClient


class Migration(BaseModel):
    TABLE_NAME = 'migrations'

    title = CharField(null=False, primary_key=True)
    apply = BooleanField(default=False)
    updated_at = TimestampField()

    def __init__(self, client: TelegramApiClient = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = client
        self.db = migrator.database
        self.meta = Introspector.from_database(self.db).metadata

    def is_applied(self):
        return self.apply == 1

    async def up(self):
        pass

    async def down(self):
        pass

    @staticmethod
    def migrate_decorator(callback: callable):
        def up(self):
            migration = Migration.get_or_none(Migration.title == self.__class__.__name__)
            if migration and migration.is_applied():
                logger.info("Migration already applied")
                return
            logger.info(f"Migrate {self.__class__.__name__} ...")
            self.client.loop.run_until_complete(callback(self))
            Migration \
                .insert(title=self.__class__.__name__, apply=True) \
                .on_conflict(update={Migration.apply: True}) \
                .execute()
            logger.info(f"Migrate {self.__class__.__name__} is done")
        return up

    @staticmethod
    def rollback_decorator(callback: callable):
        def down(self):
            migration = Migration.get_or_none(Migration.title == self.__class__.__name__)
            if not migration or not migration.is_applied():
                logger.info("Migration not applied")
                return
            logger.info(f"Rollback {self.__class__.__name__} ...")
            self.client.loop.run_until_complete(callback(self))
            migration.apply = False
            migration.save()
            logger.info(f"Rollback {self.__class__.__name__} is done")
        return down

    def async_run(self, coro, *args, **kwargs):
        return self.client.loop.run_until_complete(coro(*args, **kwargs))

    def _column_exist(self, table, column):
        return column in self.meta.get_columns(table).keys()


class CreatingTables(Migration):
    _tables = []

    @Migration.migrate_decorator
    async def up(self):
        await super().up()
        for table in self._tables:
            if table.table_exists():
                raise RuntimeError(f"Table `{table.TABLE_NAME}` already exist")

        self.db.create_tables(self._tables)
        logger.info("Creating tables is done")

    @Migration.rollback_decorator
    async def down(self):
        await super().down()
        tables = self._tables.copy()

        for table in self._tables:
            if not table.table_exists():
                tables.remove(table)
        if not tables:
            raise RuntimeError("All tables already dropped")

        self.db.drop_tables(tables)
        logger.info(f"Dropped tables: {', '.join([table.TABLE_NAME for table in tables])}")


class AddColumns(Migration):
    _tables_with_columns = {}
    """
    {
        table_name: {
            column_name: [
                migrator.add_column(*args),
                migrator.add_foreign_key_constraint(*args),
                ...
            ]
        }
    }
    """

    @Migration.migrate_decorator
    async def up(self):
        await super().up()
        ops = ()

        for table_name, columns in self._tables_with_columns.items():
            for column_name, operations_list in columns.items():
                if not self._column_exist(table_name, column_name):
                    for operation in operations_list:
                        ops = ops + (operation,)

                    logger.info(f"Column `{column_name}` added to `{table_name}`")
                else:
                    logger.info(f"Column `{column_name}` already exist in `{table_name}`")

        migrate(*ops)

    @Migration.rollback_decorator
    async def down(self):
        await super().down()
        ops = ()

        for table_name, columns in self._tables_with_columns.items():
            for column_name, operations_list in columns.items():
                if self._column_exist(table_name, column_name):
                    for operation in operations_list:
                        ops = ops + (operation,)

                    logger.info(f"Column `{column_name}` dropped from `{table_name}`")
                else:
                    logger.info(f"Column `{column_name}` already dropped from `{table_name}`")

        migrate(*ops)


class m220101000001_CreateMainTablesMigration(CreatingTables):
    _tables = [
        User,
        Chat,
        Member,
    ]


class m220101000002_CreateRolesTablesMigration(CreatingTables):
    _tables = [
        Role,
        MemberRole,
    ]


class m220101000003_CreateEventsTableMigration(CreatingTables):
    _tables = [
        QueryEvent,
    ]


class m220101000004_CreateTablesForRatingsMigration(CreatingTables):
    _tables = [
        Rating,
        RatingMember,
    ]

    def up(self):
        super().up()
        migrate(
            migrator.add_foreign_key_constraint(
                Rating.TABLE_NAME,
                'last_winner_id',
                RatingMember.TABLE_NAME,
                'id',
                on_delete='SET NULL'
            )
        )

    def down(self):
        migrate(
            migrator.drop_foreign_key_constraint(
                Rating.TABLE_NAME,
                'last_winner_id',
            )
        )
        super().down()


class m220101000005_AddMonthRatingMigration(Migration):
    @Migration.migrate_decorator
    async def up(self):
        migrate(
            migrator.add_column(
                Rating.TABLE_NAME,
                'last_month_winner_id',
                IntegerField(null=True, constraints=[SQL('AFTER last_winner_id')])
            ),
            migrator.add_foreign_key_constraint(
                Rating.TABLE_NAME,
                'last_month_winner_id',
                RatingMember.TABLE_NAME,
                'id',
                on_delete='SET NULL'
            ),
            migrator.add_column(
                Rating.TABLE_NAME,
                'last_month_run',
                DateTimeField(null=True, constraints=[SQL('AFTER last_run')])
            ),
            migrator.add_column(
                RatingMember.TABLE_NAME,
                'month_count',
                IntegerField(default=0, constraints=[SQL('AFTER count')])
            ),
            migrator.add_column(
                RatingMember.TABLE_NAME,
                'current_month_count',
                IntegerField(default=0, constraints=[SQL('AFTER month_count')])
            )
        )

    @Migration.rollback_decorator
    async def down(self):
        migrate(
            migrator.drop_foreign_key_constraint(Rating.TABLE_NAME, 'last_month_winner_id'),
            migrator.drop_column(Rating.TABLE_NAME, 'last_month_winner_id'),
            migrator.drop_column(Rating.TABLE_NAME, 'last_month_run'),
            migrator.drop_column(RatingMember.TABLE_NAME, 'month_count'),
            migrator.drop_column(RatingMember.TABLE_NAME, 'current_month_count')
        )


class m220101000006_AddInputPeerColumnForChatAndUserMigration(Migration):
    @Migration.migrate_decorator
    async def up(self):
        await super().up()
        migrate(
            migrator.add_column(
                Chat.TABLE_NAME,
                'input_peer',
                TextField(null=True)
            ),
            migrator.add_column(
                User.TABLE_NAME,
                'input_peer',
                TextField(null=True)
            )
        )

    @Migration.rollback_decorator
    async def down(self):
        await super().down()
        migrate(
            migrator.drop_column(Chat.TABLE_NAME, 'input_peer'),
            migrator.drop_column(User.TABLE_NAME, 'input_peer')
        )


class m220101000007_AddAutorunRatingColumnMigration(Migration):
    @Migration.migrate_decorator
    async def up(self):
        await super().up()
        migrate(
            migrator.add_column(
                Rating.TABLE_NAME,
                'autorun',
                BooleanField(default=False)
            )
        )

    @Migration.rollback_decorator
    async def down(self):
        await super().down()
        migrate(
            migrator.drop_column(Rating.TABLE_NAME, 'autorun')
        )


class m220101000008_AlterDudeToChatMigration(AddColumns):
    TABLE_NAME = Chat.TABLE_NAME
    COLUMN_NAME = 'dude'

    def up(self):
        self._tables_with_columns = {
            self.TABLE_NAME: {
                self.COLUMN_NAME: [
                    migrator.add_column(
                        self.TABLE_NAME,
                        self.COLUMN_NAME,
                        BooleanField(default=False)
                    )
                ]
            }
        }
        super().up()

    def down(self):
        self._tables_with_columns = {
            self.TABLE_NAME: {
                self.COLUMN_NAME: [
                    migrator.drop_column(self.TABLE_NAME, self.COLUMN_NAME)
                ]
            }
        }
        super().down()


class m230324235425_CreateRatingsLeadersTableMigration(CreatingTables):
    _tables = [
        RatingLeader,
    ]


class m230330215105_CreateCacheQuantumrandTableMigration(CreatingTables):
    _tables = [
        CacheQuantumRand
    ]
