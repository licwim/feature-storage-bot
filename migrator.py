# !/usr/bin/env python

import inspect

import click

from fsb.db import migrations
from fsb.db.migrations import *


def exit_with_message(message: str = None, code: int = 1):
    print(message)
    exit(code)


@click.group()
def migrator_cli():
    if not Migration.table_exists():
        Migration.create_table()


def get_migrations(applied: bool = None):
    class_members = inspect.getmembers(migrations, inspect.isclass)
    class_members = list(filter(
        lambda cls: issubclass(cls[1], Migration) and cls[1] != Migration and cls[0].endswith('Migration'),
        class_members
    ))
    class_members.sort(key=lambda m: inspect.getsourcelines(m[1])[1])

    position = 0
    for _, migration_class in class_members:
        position += 1
        migration_class.position = position

    if applied is None:
        result = class_members
    else:
        applied_migrations = []
        result = []
        for migration in Migration.select().where(Migration.apply == 1):
            applied_migrations.append(migration.migration_name)

        if applied:
            for migration_name, migration_class in class_members:
                if migration_name in applied_migrations:
                    result.append((migration_name, migration_class))
        else:
            for migration_name, migration_class in class_members:
                if migration_name not in applied_migrations:
                    result.append((migration_name, migration_class))

    return result


def get_migration_by_classname(ctx, param, migration_name):
    try:
        migration_object = None
        for _migration_name, _migration_class in get_migrations():
            if migration_name == _migration_name:
                migration_object = _migration_class()
                break
        assert migration_object
        return migration_object
    except AttributeError or AssertionError:
        exit_with_message("Migration not found: " + migration_name)


@click.command('up')
@click.argument('migration', callback=get_migration_by_classname)
def action_up(migration: Migration):
    click.echo(f"Migrate {migration.__class__.__name__} ...")
    migration.up()


@click.command('down')
@click.argument('migration', callback=get_migration_by_classname)
def action_down(migration: Migration):
    click.echo(f"Rollback {migration.__class__.__name__} ...")
    migration.down()


@click.command('migrate')
@click.option('-y', help='Force confirm', is_flag=True, default=False)
def action_migrate(y: bool):
    migration_list = get_migrations(applied=False)
    if not migration_list:
        click.echo('No new migrations')
        return
    migration_names, migrations_classes = map(list, zip(*migration_list))
    click.echo(f"Migrate next migrations:\n" + "\n".join(migration_names))
    if not y:
        click.confirm('Do you want to continue?', abort=True)
    for migration_class in migrations_classes:
        migration_class().up()


@click.command('rollback')
@click.argument('count', type=int, default=1)
@click.option('-y', help='Force confirm', is_flag=True, default=False)
def action_rollback(count: int, y: bool):
    migration_list = get_migrations(applied=True)
    if not migration_list:
        click.echo('No applied migrations')
        return
    migration_list.reverse()
    del migration_list[count:]
    migration_names, migrations_classes = map(list, zip(*migration_list))
    click.echo(f"Rollback next migrations:\n" + "\n".join(migration_names))
    if not y:
        click.confirm('Do you want to continue?', abort=True)
    for migration_class in migrations_classes:
        migration_class().down()


@click.command('list')
def action_list():
    class_members = get_migrations()
    class_list = []
    for class_name, _ in class_members:
        class_list.append(class_name)
    click.echo('\n'.join(class_list))


migrator_cli.add_command(action_up)
migrator_cli.add_command(action_down)
migrator_cli.add_command(action_migrate)
migrator_cli.add_command(action_rollback)
migrator_cli.add_command(action_list)


if __name__ == "__main__":
    migrator_cli()
