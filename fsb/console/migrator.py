# !/usr/bin/env python

import click

from fsb.db import db_manager


@click.group('migrator')
def migrator_cli():
    """Migrator"""


@click.command('migrate')
@click.argument('count', type=int, default=0)
@click.option('-d', help='Dry run', is_flag=True, default=False)
@click.option('-y', help='Force confirm', is_flag=True, default=False)
def action_migrate(count, d: bool, y: bool):
    if not db_manager.diff:
        click.echo('No new migrations')
        return

    diff = db_manager.diff if not count else db_manager.diff[:count]
    click.echo(f"Migrate next migrations:\n" + "\n".join(diff))

    if not y:
        click.confirm('Do you want to continue?', abort=True)
    db_manager.upgrade(count, d)


@click.command('rollback')
@click.argument('count', type=int, default=1)
@click.option('-d', help='Dry run', is_flag=True, default=False)
@click.option('-y', help='Force confirm', is_flag=True, default=False)
def action_rollback(count, d: bool, y: bool):
    if not db_manager.db_migrations:
        click.echo('No applied migrations')
        return

    diff = db_manager.db_migrations[:-1 * (count + 1):-1]
    click.echo(f"Rollback next migrations:\n" + "\n".join(diff))

    if not y:
        click.confirm('Do you want to continue?', abort=True)
    db_manager.downgrade(count, d)


@click.command('status')
def action_status():
    db_manager.status()


@click.command('create')
@click.argument('name', type=str)
def action_create(name):
    db_manager.revision(name)


@click.command('create-model')
@click.argument('model', type=str)
def action_create_model(model):
    db_manager.create('fsb.db.models.' + model)


@click.command('delete')
@click.argument('name', type=str)
@click.option('-y', help='Force confirm', is_flag=True, default=False)
def action_delete(name, y: bool):
    if not y:
        click.confirm(f'Delete migration: {db_manager.find_migration(name)}?', abort=True)
    db_manager.delete(name)


migrator_cli.add_command(action_migrate)
migrator_cli.add_command(action_rollback)
migrator_cli.add_command(action_status)
migrator_cli.add_command(action_create)
migrator_cli.add_command(action_create_model)
migrator_cli.add_command(action_delete)
