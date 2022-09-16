# !/usr/bin/env python

from fsb.console import cli
from fsb.console.common import month_rating_calc, broadcast_message, day_rating_roll
from fsb.console.migrator import migrator_cli

cli.add_command(migrator_cli)
cli.add_command(month_rating_calc)
cli.add_command(broadcast_message)
cli.add_command(day_rating_roll)

if __name__ == "__main__":
    cli()
