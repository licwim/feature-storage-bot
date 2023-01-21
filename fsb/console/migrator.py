# !/usr/bin/env python

import inspect
import click
from convert_case import pascal_case
from datetime import datetime

from fsb.console import client, exit_with_message
from fsb.db import migrations
from fsb.db.migrations import Migration


@click.group('migrator')
def migrator_cli():
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

    result = {}
    for migration_name, migration_class in class_members:
        result[migration_name] = {
            'cls': migration_class,
            'obj': None,
        }

    for migration in Migration.select():
        if migration.title in result.keys():
            result[migration.title]['obj'] = migration
        else:
            result[migration.title] = {
                'cls': None,
                'obj': migration
            }

    return [item[1] for item in sorted(result.items(), key=lambda item: item[0])]


def get_migration_by_classname(ctx, param, migration_name):
    try:
        migration_list = get_migrations()
        resulted_migration = None

        for migration in migration_list:
            if migration_name == migration['cls'].__name__:
                resulted_migration = migration
                break

        assert issubclass(resulted_migration['cls'], Migration)
        return resulted_migration
    except AttributeError or AssertionError:
        exit_with_message("Migration not found: " + migration_name)


@click.command('up')
@click.argument('migration', callback=get_migration_by_classname)
def action_up(migration: Migration):
    click.echo(f"Migrate {migration.__class__.__name__} ...")
    migration['cls'](client).up()


@click.command('down')
@click.argument('migration', callback=get_migration_by_classname)
def action_down(migration: Migration):
    click.echo(f"Rollback {migration.__class__.__name__} ...")
    migration['cls'](client).down()


@click.command('migrate')
@click.argument('count', type=int, default=0)
@click.option('-y', help='Force confirm', is_flag=True, default=False)
def action_migrate(count: int, y: bool):
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
def action_rollback(count: int, y: bool):
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
def action_list():
    migration_list = get_migrations()
    result = []
    for migration in migration_list:
        result.append(('[x] ' if migration['obj'] and migration['obj'].apply == 1 else '[] ') + migration['cls'].__name__)
    click.echo('\n'.join(result))


@click.command('create')
@click.argument('name', type=str)
def action_create(name):
    name = datetime.today().strftime('m%y%m%d%H%M%S_') \
        + pascal_case(name) + 'Migration'
    filename = inspect.getsourcefile(migrations)
    up = inspect.getsource(Migration.up)
    down = inspect.getsource(Migration.down)
    migration_template = f"\n\nclass {name}(Migration):\n" \
                         f"    @Migration.migrate_decorator\n" \
                         f"{up}\n" \
                         f"    @Migration.rollback_decorator\n" \
                         f"{down}"
    click.confirm(f'Create a migration titled {name}?', abort=True)
    with open(filename, 'a', encoding='utf-8') as fd:
        if fd.write(migration_template):
            click.echo('Migration is created.')
        else:
            click.echo('Failed.')


migrator_cli.add_command(action_up)
migrator_cli.add_command(action_down)
migrator_cli.add_command(action_migrate)
migrator_cli.add_command(action_rollback)
migrator_cli.add_command(action_list)
migrator_cli.add_command(action_create)
