# !/usr/bin/env python
import yaml


class InfoBuilder:

    def build_message_info(event):
        match event.chat.__class__.__name__:
            case 'Chat' | 'Channel':
                chat_info = {
                    'id': event.chat_id,
                    'title': event.chat.title,
                    'type': event.chat.__class__.__name__,
                    'sender': {
                        'id': event.sender.id,
                        'username': event.sender.username,
                    }
                }
            case 'User':
                chat_info = {
                    'id': event.chat_id,
                    'username': event.chat.username,
                    'type': event.chat.__class__.__name__,
                }
            case _:
                chat_info = None

        data_info = {
            'chat': chat_info,
            'text': event.message.text,
        }

        return yaml.dump(data_info, sort_keys=False, default_flow_style=False)

    def build_entity_info(entity):
        match entity.__class__.__name__:
            case 'Chat' | 'Channel':
                data_info = {
                    'id': entity.id,
                    'title': entity.title,
                    'type': entity.__class__.__name__,
                }
            case 'User':
                data_info = {
                    'id': entity.id,
                    'username': entity.username,
                    'type': entity.__class__.__name__,
                }
            case _:
                data_info = None

        return yaml.dump(data_info, sort_keys=False, default_flow_style=False)

    build_message_info = staticmethod(build_message_info)
    build_entity_info = staticmethod(build_entity_info)
