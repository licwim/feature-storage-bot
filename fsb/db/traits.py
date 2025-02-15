# !/usr/bin/env python

from datetime import datetime

from peewee import DateTimeField, SQL


class CreatedAtTrait:
    created_at = DateTimeField(default=datetime.now(), constraints=[SQL('DEFAULT CURRENT_TIMESTAMP')])



class UpdatedAtTrait:
    updated_at = DateTimeField(default=datetime.now(),
                               constraints=[SQL('DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')])


class CreatedUpdatedAtTrait(CreatedAtTrait, UpdatedAtTrait):
    pass
