from typing import Union

from telethon.tl.types import User, Chat


class ChatHelper:

    def __init__(self, chat: Union[Chat, User]) -> None:
        self.base = chat

        if isinstance(chat, Chat):
            self.name = chat.title
        elif isinstance(chat, User):
            self.name = chat.username
        else:
            raise TypeError(type(chat), "Wrong type for ChatHelper")

        self.id = chat.id
