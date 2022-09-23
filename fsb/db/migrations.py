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
)
from fsb.handlers.ratings import PIDOR_KEYWORD, CHAD_KEYWORD
from fsb.helpers import Helper
from fsb.telegram.client import TelegramApiClient


class Migration(BaseModel):
    TABLE_NAME = 'migrations'
    position = 0

    id = IntegerField(primary_key=True)
    migration_name = CharField(null=False, unique=True)
    apply = BooleanField(default=False)
    updated_at = TimestampField()

    def __init__(self, client: TelegramApiClient = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = client
        self.db = migrator.database

    def is_applied(self):
        return self.apply == 1

    async def up(self):
        pass

    async def down(self):
        pass

    @staticmethod
    def migrate_decorator(callback: callable):
        def up(self):
            migration = Migration.get_or_none(Migration.migration_name == self.__class__.__name__)
            if migration and migration.is_applied():
                logger.info("Migration already applied")
                return
            logger.info(f"Migrate {self.__class__.__name__} ...")
            self.client.loop.run_until_complete(callback(self))
            Migration \
                .insert(id=self.position, migration_name=self.__class__.__name__, apply=1) \
                .on_conflict(update={Migration.apply: 1}) \
                .execute()
            logger.info(f"Migrate {self.__class__.__name__} is done")
        return up

    @staticmethod
    def rollback_decorator(callback: callable):
        def down(self):
            migration = Migration.get_or_none(Migration.migration_name == self.__class__.__name__)
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


class AddPidorAndChadRatingsMigration(Migration):
    _chats = [
        1511700614
    ]

    @Migration.migrate_decorator
    async def up(self):
        await super().up()
        for chat_id in self._chats:
            tg_chat = await self.client.get_entity(chat_id)
            db_chat = Chat.get_or_create(
                telegram_id=tg_chat.id,
                defaults={
                    'name': tg_chat.title,
                    'type': Chat.get_chat_type(tg_chat)
                }
            )[0]

            for tg_member in await self.client.get_dialog_members(tg_chat):
                user = User.get_or_create(
                    telegram_id=tg_member.id,
                    defaults={
                        'name': Helper.make_member_name(tg_member, with_username=False),
                        'nickname': tg_member.username
                    }
                )[0]
                Member.get_or_create(chat=db_chat, user=user)

            Rating.get_or_create(
                name=PIDOR_KEYWORD,
                chat=db_chat,
                defaults={
                    'command': PIDOR_KEYWORD
                }
            )

            Rating.get_or_create(
                name=CHAD_KEYWORD,
                chat=db_chat,
                defaults={
                    'command': CHAD_KEYWORD
                }
            )

    @Migration.rollback_decorator
    async def down(self):
        await super().down()
        for chat_id in self._chats:
            tg_chat = await self.client.get_entity(chat_id)
            db_chat = Chat.get(telegram_id=tg_chat.id)

            for rating in Rating.select().where(Rating.chat == db_chat):
                rating.delete_instance()


class AddMonthRatingMigration(Migration):
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
            )
        )

    @Migration.rollback_decorator
    async def down(self):
        migrate(
            migrator.drop_foreign_key_constraint(Rating.TABLE_NAME, 'last_month_winner_id'),
            migrator.drop_column(Rating.TABLE_NAME, 'last_month_winner_id'),
            migrator.drop_column(RatingMember.TABLE_NAME, 'month_count')
        )


class AddInputPeerColumnForChatAndUserMigration(Migration):
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
