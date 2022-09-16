# !/usr/bin/env python

from fsb.console import cli
from fsb.console.common import month_rating_calc
from fsb.console.migrator import migrator_cli

cli.add_command(migrator_cli)
cli.add_command(month_rating_calc)

if __name__ == "__main__":
    cli()
