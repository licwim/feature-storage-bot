# !/usr/bin/env python

from peewee import MySQLDatabase
from playhouse.migrate import MySQLMigrator

from fsb.config import Config

base_db = MySQLDatabase(Config.db_name, user=Config.db_user, password=Config.db_password,
                        host=Config.db_host, port=3306)
base_migrator = MySQLMigrator(base_db)
