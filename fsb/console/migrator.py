# !/usr/bin/env python

import click

from fsb.db import db_manager


@click.group('migrator')
def migrator_cli():
    """Migrator"""


@click.command('migrate')
@click.argument('name', type=str, default='')
@click.option('-d', help='Dry run', is_flag=True, default=False)
@click.option('-y', help='Force confirm', is_flag=True, default=False)
def action_migrate(name, d: bool, y: bool):
    name = db_manager.find_migration(name) if name else None

    if not db_manager.diff:
        click.echo('No new migrations')
        return

    click.echo(f"Migrate next migrations:\n" + name if name else "\n".join(db_manager.diff))

    if not y:
        click.confirm('Do you want to continue?', abort=True)
    db_manager.upgrade(name, d)


@click.command('rollback')
@click.argument('name', type=str, default='')
@click.option('-d', help='Dry run', is_flag=True, default=False)
@click.option('-y', help='Force confirm', is_flag=True, default=False)
def action_rollback(name, d: bool, y: bool):
    name = db_manager.find_migration(name) if name else None

    if not db_manager.db_migrations:
        click.echo('No applied migrations')
        return

    click.echo(f"Rollback next migrations:\n" + (name if name else db_manager.db_migrations[-1]))

    if not y:
        click.confirm('Do you want to continue?', abort=True)
    db_manager.downgrade(name, d)


@click.command('status')
def action_status():
    db_manager.status()


@click.command('create')
@click.argument('name', type=str)
def action_create(name):
    db_manager.revision(name)


@click.command('create_model')
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
