# !/usr/bin/env python

from fsb.console import cli
from fsb.console.common import broadcast_message
from fsb.console.migrator import migrator_cli
from fsb.console.ratings import ratings

cli.add_command(migrator_cli)
cli.add_command(broadcast_message)
cli.add_command(ratings)

if __name__ == "__main__":
    cli()
