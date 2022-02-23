# !/usr/bin/env python
from time import sleep

from . import FSB_DEV_MODE
from . import logger
from .config import Config
from .controllers import HandlersController
from .telegram.client import TelegramApiClient


class FeatureStorageBot:

    STOP_TIMEOUT = 60

    def __init__(self):
        self.client = TelegramApiClient(Config.bot_username)
        self.loop = self.client.loop
        self.handlers_controller = HandlersController(self.client)

    def run(self):
        logger.info(f"Development mode is {'ON' if FSB_DEV_MODE else 'OFF'}")
        self.loop.run_until_complete(self.client.connect(True))

        try:
            self.client.start()
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        logger.info("Bot stopping ...")

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
