# !/usr/bin/env python

from fsb.console import cli
from fsb.console.migrator import migrator_cli

cli.add_command(migrator_cli)

if __name__ == "__main__":
    cli()
