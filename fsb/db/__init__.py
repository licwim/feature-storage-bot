# !/usr/bin/env python

from fsb.config import config
from peewee_async import PooledMySQLDatabase
from playhouse.migrate import MySQLMigrator
from playhouse.shortcuts import ReconnectMixin

MAX_DB_CONNECTIONS = 10


class ReconnectedPooledDatabase(ReconnectMixin, PooledMySQLDatabase):
    pass


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
