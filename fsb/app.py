# !/usr/bin/env python
from time import sleep

from . import logger
from .config import Config
from .controllers import HandlersController
from .telegram.client import TelegramApiClient
from .utils.inputlistener import InputListener


class FeatureStorageBot:

    STOP_TIMEOUT = 60

    def __init__(self):
        self.client = TelegramApiClient(Config.bot_username, Config.api_id, Config.api_hash)
        self.loop = self.client.loop
        self.handlers_controller = HandlersController(self.client)
        self.input_listener = InputListener()

    def run(self):
        self.loop.run_until_complete(self.client.connect(Config.bot_token))
        self.input_listener.add_event('exit', self.stop)

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
        self.input_listener.stop()
