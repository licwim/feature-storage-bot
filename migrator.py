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
    def _migration_need_decorator(callback: callable):
        def action(self):
            if self.migration:
                callback(self)
            else:
                exit_with_message("Migration must be specified")
        return action

    @_migration_need_decorator
    def migrate(self):
        self.migration.up()

    @_migration_need_decorator
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

    @staticmethod
    def help():
        commands = []
        for i in inspect.getmembers(Migrator):
            if not i[0].startswith('_'):
                if inspect.ismethod(i[1]) or inspect.isfunction(i[1]):
                    commands.append('  - ' + i[0])

        print('Available commands:\n' + '\n'.join(commands))


if len(sys.argv) == 3:
    command = sys.argv[1]
    migration_class = sys.argv[2]
    try:
        migration = getattr(migrations, migration_class)()
        assert isinstance(migration, BaseMigration)
    except AttributeError or AssertionError:
        exit_with_message("Migration not found: " + migration_class)
elif len(sys.argv) == 2:
    command = sys.argv[1]
    migration = None
else:
    command = 'help'
    migration = None

migrator = Migrator(migration)

try:
    action = getattr(migrator, command)
    action()
except AttributeError:
    exit_with_message("Unsupported method: " + sys.argv[1])
