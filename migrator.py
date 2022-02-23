# !/usr/bin/env python

import sys

from fsb.db import migrations
from fsb.db.migrations import *


class Migrator:
    @staticmethod
    def migrate(migration: BaseMigration):
        migration.up()

    @staticmethod
    def rollback(migration: BaseMigration):
        migration.down()


if len(sys.argv) < 3:
    exit(1)

migration = getattr(migrations, sys.argv[2])()
assert isinstance(migration, BaseMigration)

match sys.argv[1]:
    case 'migrate':
        Migrator.migrate(migration)
    case 'rollback':
        Migrator.rollback(migration)
