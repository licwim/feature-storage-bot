# !/usr/bin/env python

from fsb.console import cli
from fsb.console.birthday import birthday
from fsb.console.common import dude_broadcast, new_year_broadcast
from fsb.console.message import send_message_command, countdown
from fsb.console.migrator import migrator_cli
from fsb.console.ratings import ratings

cli.add_command(migrator_cli)
cli.add_command(send_message_command)
cli.add_command(ratings)
cli.add_command(dude_broadcast)
cli.add_command(new_year_broadcast)
cli.add_command(countdown)
cli.add_command(birthday)

if __name__ == "__main__":
    cli()
