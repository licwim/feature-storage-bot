# !/usr/bin/env python

from datetime import datetime

from peewee import DateTimeField, TextField, SQL

from fsb.db import ModelInterface


class ModelTraitInterface(ModelInterface):
    pass


class CreatedAtTrait(ModelTraitInterface):
    created_at = DateTimeField(default=datetime.now, constraints=[SQL('DEFAULT CURRENT_TIMESTAMP')])


class UpdatedAtTrait(ModelTraitInterface):
    updated_at = DateTimeField(default=datetime.now,
                               constraints=[SQL('DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')])


class CreatedUpdatedAtTrait(CreatedAtTrait, UpdatedAtTrait):
    pass


class DeletedAtTrait(ModelTraitInterface):
    deleted_at = DateTimeField(null=True)

    def mark_as_deleted(self):
        self.deleted_at = datetime.now()

    def mark_as_undeleted(self):
        self.deleted_at = None

    @classmethod
    def only_undeleted(cls):
        try:
            select = cls.select().where(cls.deleted_at.is_null())
            return select
        except AttributeError:
            return None

    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class DeletedAtWithReasonTrait(DeletedAtTrait):
    deletion_reason = TextField(null=True)

    def mark_as_deleted(self, reason = None):
        if reason:
            self.deletion_reason = reason

        super().mark_as_deleted()

    def mark_as_undeleted(self):
        self.deletion_reason = None
        super().mark_as_undeleted()
