# !/usr/bin/env python

from datetime import datetime
from time import sleep

import click

from fsb.config import config
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

    for rating in Rating.select().where(Rating.autorun):
        if rating.last_month_winner \
                and rating.last_month_run \
                and rating.last_month_run >= datetime.today().replace(hour=0, minute=0, second=0, microsecond=0, day=1):
            continue

        if config.FOOL_DAY:
            await ratings_service.fool_roll(rating, rating.chat.telegram_id, True)
        else:
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

        if config.FOOL_DAY:
            await ratings_service.fool_roll(rating, rating.chat.telegram_id)
        else:
            await ratings_service.roll(rating, rating.chat.telegram_id)

        sleep(1)


@click.command('year-roll')
@coro
async def year_roll():
    """Calculation of the ratings winners of the year"""
    ratings_service = RatingService(client)

    for rating in Rating.select().where(Rating.autorun):
        if not (rating.last_month_winner
                and rating.last_month_run
                and rating.last_month_run >= datetime.today().replace(hour=0, minute=0, second=0, microsecond=0, day=1)):
            await ratings_service.roll(rating, rating.chat.telegram_id, True)

        if not (rating.last_year_winner
                and rating.last_year_run
                and rating.last_year_run >= datetime.today().replace(hour=0, minute=0, second=0, microsecond=0, day=1, month=1)):
            await ratings_service.roll_year(rating, rating.chat.telegram_id)

        sleep(1)


@click.command('natural-not-found')
@coro
async def natural_not_found():
    """Sending not found message for all chats with natural ratings"""
    rating_service = RatingService(client)

    for rating in Rating.select().where(Rating.command == 'natural'):
        stat_message = await rating_service.get_stat_message(rating, False)
        main_message = 'В этом чате натуралы все еще не обнаружены'

        await client.send_message(rating.chat.telegram_id, stat_message)
        await client.send_message(rating.chat.telegram_id, main_message)

ratings.add_command(month_roll)
ratings.add_command(day_roll)
ratings.add_command(year_roll)
ratings.add_command(natural_not_found)
