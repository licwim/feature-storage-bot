# !/usr/bin/env python

from datetime import datetime

import click

from fsb.console import client
from fsb.db.models import Rating, RatingMember
from fsb.handlers.ratings import RatingCommandHandler
from fsb.helpers import Helper


@click.command('month-rating-calc')
def month_rating_calc():
    for rating in Rating.select():
        if rating.last_month_winner \
                and rating.last_month_run \
                and rating.last_month_run >= datetime.today().replace(hour=0, minute=0, second=0, microsecond=0, day=1):
            continue

        match rating.command:
            case RatingCommandHandler.PIDOR_COMMAND:
                msg_name = 'ПИДОР'
            case RatingCommandHandler.CHAD_COMMAND:
                msg_name = 'КРАСАВЧИК'
            case _:
                raise RuntimeError

        rating_members = RatingMember.select()\
            .where(RatingMember.rating == rating)\
            .order_by(RatingMember.month_count.desc())
        actual_members = client.sync_get_dialog_members(rating.chat.telegram_id)
        members_collection = Helper.collect_members(actual_members, rating_members)
        if not members_collection:
            return

        win_tg_member, win_db_member = members_collection[0]
        for tg_member, db_member in members_collection:
            db_member.month_count = 0
            db_member.save()

        member_name = Helper.make_member_name(win_tg_member, with_mention=True)
        rating.last_month_winner = win_db_member
        rating.last_month_run = datetime.now()
        rating.save()

        client.sync_send_message(rating.chat.telegram_id, RatingCommandHandler.MONTH_WINNER_MESSAGE_PATTERN.format(
            msg_name=msg_name,
            member_name=member_name
        ) + "\nПоздравляем! 🎉")
