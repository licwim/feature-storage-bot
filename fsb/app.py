# !/usr/bin/env python
import logging
from time import sleep

from fsb.config import config
from fsb.db.models import Chat
from fsb.loaders import ControllerLoader
from fsb.services import ChatService
from fsb.telegram.client import TelegramApiClient


async def before_start(client):
    chat_service = ChatService(client)

    for chat in Chat.select():
        entity = await client.get_entity(chat.telegram_id)
        await chat_service.create_chat(entity=entity, update=True)


class FeatureStorageBot:

    STOP_TIMEOUT = 60

    def __init__(self):
        self.client = TelegramApiClient(config.BOT_USERNAME)
        self.loop = self.client.loop
        self.controller_loader = ControllerLoader(self.client)
        self.logger = logging.getLogger('main')

    def run(self):
        self.logger.info(f"Development mode is {'ON' if config.FSB_DEV_MODE else 'OFF'}")
        self.controller_loader.run_objects()
        self.loop.run_until_complete(self.client.connect(True))
        self.loop.run_until_complete(before_start(self.client))

        try:
            self.client.start()
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        self.logger.info("Bot stopping ...")

        if self.loop.is_running():
            exit_task = self.loop.create_task(self.client.exit())
        else:
            exit_task = self.loop.run_until_complete(self.client.exit())

        timeout = 0
        while not (exit_task.done() or exit_task.cancelled()):
            sleep(1)
            timeout += 1
            if timeout > self.STOP_TIMEOUT:
                raise TimeoutError("Timeout for program completion exceeded")

        if self.loop.is_running():
            self.loop.stop()
        if not self.loop.is_closed():
            self.loop.close()
