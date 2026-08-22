# -*- coding: utf-8 -*-
SCHEMA = {
    'type': 'object',
    'properties': {
        'success': {'type': 'boolean'},
        'message': {'type': 'string'},
        'new_state': {'type': 'string'},
        'durability_delta': {'type': 'integer', 'minimum': -100, 'maximum': 0},
        'remove_item': {'type': 'boolean'}
    },
    'required': ['success', 'message', 'new_state', 'durability_delta', 'remove_item'],
    'additionalProperties': False
}
OBJ_SCHEMA = {
    'type': 'object',
    'properties': {'success': {'type': 'boolean'}, 'message': {'type': 'string'}},
    'required': ['success', 'message'],
    'additionalProperties': False
}


class InteractionAI:
    def item_action(self, command, item, source, world, qwen):
        sys = (
            'Ты физический движок взаимодействия. Рассматривай только данный предмет и его свойства. '
            'Любое физически осмысленное действие допустимо. Не создавай новые предметы, комнаты, существ или крупные события. '
            'Не меняй инвентарь самовольно. Верни только JSON.'
        )
        user = (
            f"Предмет: {item.get('name')}\n"
            f"Описание: {item.get('description')}\n"
            f"Состояние: {item.get('state')}\n"
            f"Свойства: {', '.join(item.get('properties', []))}\n"
            f"Прочность: {item.get('durability', 100)}\n"
            f"Источник: {source}\n"
            f"Команда: {command}"
        )
        raw = qwen.chat(sys, user, max_tokens=90, temperature=.15, response_format={'type': 'json_schema', 'json_schema': {'name': 'item_action', 'schema': SCHEMA, 'strict': True}}, timeout=12)
        data = qwen.parse_json(raw)
        return data or {
            'success': False,
            'message': f"Ты пытаешься взаимодействовать с {item.get('name', 'предмет')}, но заметного результата нет.",
            'new_state': item.get('state', 'обычное состояние'),
            'durability_delta': 0,
            'remove_item': False
        }

    def object_action(self, command, obj, room, qwen):
        sys = 'Ты физический движок взаимодействия с объектом окружающей среды. Только непосредственный реалистичный результат. Без новых предметов, существ, комнат и крупных событий. Только JSON.'
        user = f"Объект: {obj}\nОписание комнаты: {room.get('description', '')}\nКоманда: {command}"
        raw = qwen.chat(sys, user, max_tokens=60, temperature=.15, response_format={'type': 'json_schema', 'json_schema': {'name': 'object_action', 'schema': OBJ_SCHEMA, 'strict': True}}, timeout=10)
        data = qwen.parse_json(raw)
        return (data or {}).get('message') or f'Ты взаимодействуешь с {obj}.'

    def free_action(self, command, room, world, qwen):
        # Свободная AI-генерация теперь вызывается только для реально понятных действий.
        sys = (
            'Ты физический рассказчик игры. Опиши только непосредственный реалистичный результат команды '
            'в текущем месте. Если команда не является понятным физическим действием, верни ровно: '
            'Я не понял, какое действие выполнить. Не создавай предметов, существ, комнат или крупных событий. '
            'Только 1-2 коротких предложения на русском.'
        )
        user = (
            f"Место: {room.get('title', '')}\n"
            f"Описание: {room.get('description', '')}\n"
            f"Предметы: {', '.join(i['name'] for i in room.get('items', []))}\n"
            f"Объекты: {', '.join(room.get('objects', []))}\n"
            f"Команда: {command}"
        )
        return qwen.chat(sys, user, max_tokens=55, temperature=.15, timeout=8) or 'Я не понял, какое действие выполнить.'
