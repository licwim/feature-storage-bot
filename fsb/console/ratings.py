# !/usr/bin/env python

from datetime import datetime
from time import sleep

import click

from fsb.console import client, coro
from fsb.db.models import Rating
from fsb.services import RatingService


@click.group('ratings')
def ratings():
    """Ratings commands"""
    pass


@click.command('month-roll')
@coro
async def month_roll():
    """Calculation of the ratings winners of the month"""

    ratings_service = RatingService(client)

    for rating in Rating.select():
        if rating.last_month_winner \
                and rating.last_month_run \
                and rating.last_month_run >= datetime.today().replace(hour=0, minute=0, second=0, microsecond=0, day=1):
            continue

        await ratings_service.roll(rating, rating.chat.telegram_id, True)
        sleep(1)


@click.command('day-roll')
@coro
async def day_roll():
    """Run ratings commands"""

    ratings_service = RatingService(client)

    for rating in Rating.select().where(Rating.autorun):
        if rating.last_run \
                and rating.last_run >= datetime.today().replace(hour=0, minute=0, second=0, microsecond=0):
            continue

        await ratings_service.roll(rating, rating.chat.telegram_id)
        sleep(1)

ratings.add_command(month_roll)
ratings.add_command(day_roll)
