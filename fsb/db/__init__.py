# !/usr/bin/env python

from peewee_async import PooledMySQLDatabase
from playhouse.migrate import MySQLMigrator
from playhouse.shortcuts import ReconnectMixin

from fsb.config import Config


class ReconnectedPooledDatabase(ReconnectMixin, PooledMySQLDatabase):
    pass


base_db = ReconnectedPooledDatabase(
    database=Config.db_name,
    user=Config.db_user,
    password=Config.db_password,
    host=Config.db_host,
    port=3306,
    max_connections=Config.MAX_DB_CONNECTIONS
)

base_migrator = MySQLMigrator(base_db)
