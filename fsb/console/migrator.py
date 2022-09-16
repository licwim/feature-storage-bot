# !/usr/bin/env python

import inspect

import asyncclick as click

from fsb.console import client, exit_with_message
from fsb.db import migrations
from fsb.db.migrations import Migration


@click.group('migrator')
async def migrator_cli():
    """Migrator"""

    if not Migration.table_exists():
        Migration.create_table()


def get_migrations():
    class_members = inspect.getmembers(migrations, inspect.isclass)
    class_members = list(filter(
        lambda cls: issubclass(cls[1], Migration) and cls[1] != Migration and cls[0].endswith('Migration'),
        class_members
    ))
    class_members.sort(key=lambda m: inspect.getsourcelines(m[1])[1])

    position = 0
    result = []
    for migration_name, migration_class in class_members:
        position += 1
        migration_class.position = position
        result.append({
            'cls': migration_class,
            'obj': None,
        })

    for migration in Migration.select():
        result[migration.id - 1]['obj'] = migration

    return result


def get_migration_by_classname(ctx, param, migration_name):
    try:
        migration_list = get_migrations()
        migration_object = None

        for migration in migration_list:
            if migration_name == migration['cls'].__name__:
                if migration['obj']:
                    migration_object = migration['obj']
                else:
                    migration_object = migration['cls'](client)

        assert isinstance(migration_object, Migration)
        return migration_object
    except AttributeError or AssertionError:
        exit_with_message("Migration not found: " + migration_name)


@click.command('up')
@click.argument('migration', callback=get_migration_by_classname)
async def action_up(migration: Migration):
    click.echo(f"Migrate {migration.__class__.__name__} ...")
    migration.up()


@click.command('down')
@click.argument('migration', callback=get_migration_by_classname)
async def action_down(migration: Migration):
    click.echo(f"Rollback {migration.__class__.__name__} ...")
    migration.down()


@click.command('migrate')
@click.argument('count', type=int, default=0)
@click.option('-y', help='Force confirm', is_flag=True, default=False)
async def action_migrate(count: int, y: bool):
    migration_list = get_migrations()
    migration_names = []
    for migration in migration_list.copy():
        if migration['obj'] and migration['obj'].apply == 1:
            migration_list.remove(migration)
        else:
            migration_names.append(migration['cls'].__name__)
    if not migration_list:
        click.echo('No new migrations')
        return

    if count:
        del migration_list[count:]
        del migration_names[count:]

    click.echo(f"Migrate next migrations:\n" + "\n".join(migration_names))

    if not y:
        click.confirm('Do you want to continue?', abort=True)
    for migration in migration_list:
        migration['cls'](client).up()


@click.command('rollback')
@click.argument('count', type=int, default=1)
@click.option('-y', help='Force confirm', is_flag=True, default=False)
async def action_rollback(count: int, y: bool):
    migration_list = get_migrations()
    migration_list.reverse()
    migration_names = []
    for migration in migration_list.copy():
        if not migration['obj'] or migration['obj'].apply == 0:
            migration_list.remove(migration)
        else:
            migration_names.append(migration['cls'].__name__)
    if not migration_list:
        click.echo('No applied migrations')
        return

    del migration_list[count:]
    del migration_names[count:]

    click.echo(f"Rollback next migrations:\n" + "\n".join(migration_names))

    if not y:
        click.confirm('Do you want to continue?', abort=True)
    for migration in migration_list:
        migration['cls'](client).down()


@click.command('list')
async def action_list():
    migration_list = get_migrations()
    result = []
    for migration in migration_list:
        result.append(('[x] ' if migration['obj'] and migration['obj'].apply == 1 else '[] ') + migration['cls'].__name__)
    click.echo('\n'.join(result))


migrator_cli.add_command(action_up)
migrator_cli.add_command(action_down)
migrator_cli.add_command(action_migrate)
migrator_cli.add_command(action_rollback)
migrator_cli.add_command(action_list)
