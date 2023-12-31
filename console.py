# !/usr/bin/env python

import click

from fsb.console import cli
from fsb.console.common import broadcast_message, dude_broadcast, new_year_broadcast
from fsb.console.migrator import migrator_cli
from fsb.console.ratings import ratings

cli.add_command(migrator_cli)
cli.add_command(broadcast_message)
cli.add_command(ratings)
cli.add_command(dude_broadcast)
cli.add_command(new_year_broadcast)

if __name__ == "__main__":
    cli()
