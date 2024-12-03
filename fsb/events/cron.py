# !/usr/bin/env python

from typing import Union

from fsb.db.models import QueryEvent, CronJob
from telethon import Button


class CronQueryEvent(QueryEvent):
    def __init__(self, sender_id: int = None, cron_job_id: int = None):
        self.cron_job_id = cron_job_id
        self.cron_job = None
        super().__init__(sender_id, self.build_data_dict())

    def build_data_dict(self) -> dict:
        return {
            'cron_job_id': self.cron_job_id,
        }

    @classmethod
    def normalize_data_dict(cls, data_dict: dict) -> dict:
        data_dict = super().normalize_data_dict(data_dict)
        for key in ['cron_job_id']:
            if key not in data_dict['data']:
                data_dict['data'][key] = None
        return data_dict

    @classmethod
    def from_dict(cls, data_dict: dict) -> QueryEvent:
        data_dict = cls.normalize_data_dict(data_dict)
        sender_id = data_dict['sender_id']
        data = data_dict['data']
        return cls(sender_id=sender_id, cron_job_id=data['cron_job_id'])

    def get_cron_job(self) -> Union[CronJob, None]:
        if not self.cron_job and self.cron_job_id:
            self.cron_job = CronJob.get_by_id(self.cron_job_id)

        return self.cron_job


class GeneralMenuCronEvent(CronQueryEvent):
    @staticmethod
    def get_message_and_buttons(sender_id) -> tuple:
        return "Меню планировщика", [
            [Button.inline('Список задач', ListCronEvent(sender_id).save_get_id())],
            [Button.inline('Добавить задачу', CreateCronEvent(sender_id).save_get_id()),],
            [Button.inline('Закрыть', CloseGeneralMenuCronEvent(sender_id).save_get_id())]
        ]


class CreateCronEvent(CronQueryEvent):
    pass


class ListCronEvent(CronQueryEvent):
    pass


class MenuCronEvent(CronQueryEvent):
    pass


class DeleteCronEvent(CronQueryEvent):
    pass


class ChangeCronEvent(CronQueryEvent):
    pass


class TruncateCronEvent(CronQueryEvent):
    pass


class CloseGeneralMenuCronEvent(CronQueryEvent):
    pass


class ActiveToggleCronEvent(CronQueryEvent):
    pass
