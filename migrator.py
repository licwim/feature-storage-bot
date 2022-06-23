# !/usr/bin/env python

import sys
import inspect

from fsb.db import migrations
from fsb.db.migrations import *


def exit_with_message(message: str = None, code: int = 1):
    print(message)
    exit(code)


class Migrator:
    def __init__(self, migration: BaseMigration = None):
        self.migration = migration

    @staticmethod
    def migration_need_decorator(callback: callable):
        def action(self):
            if self.migration:
                callback()
            else:
                exit_with_message("Migration must be specified")
        return action

    @migration_need_decorator
    def migrate(self):
        self.migration.up()

    @migration_need_decorator
    def rollback(self):
        self.migration.down()

    @staticmethod
    def list():
        class_members = inspect.getmembers(migrations, inspect.isclass)
        class_list = []
        for class_name, class_object in class_members:
            if issubclass(class_object, BaseMigration) and class_object != BaseMigration:
                class_list.append(class_name)
        print('\n'.join(class_list))


if len(sys.argv) == 3:
    try:
        migration = getattr(migrations, sys.argv[2])()
        assert isinstance(migration, BaseMigration)
    except AttributeError or AssertionError:
        exit_with_message("Migration not found: " + sys.argv[2])
elif len(sys.argv) == 2:
    migration = None
else:
    exit(1)

migrator = Migrator(migration)

try:
    action = getattr(migrator, sys.argv[1])
    action()
except AttributeError:
    exit_with_message("Unsupported method: " + sys.argv[1])
