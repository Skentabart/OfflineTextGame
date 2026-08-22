# -*- coding: utf-8 -*-
import random

class CombatSystem:
    def __init__(self, game):
        self.game = game
        self.rng = random.Random()

    def enemies(self):
        return self.game.world.data.setdefault('enemies', [])

    def active(self):
        room_id = self.game.world.room_id()
        return [e for e in self.enemies() if e.get('alive', True) and e.get('room_id') == room_id]

    def spawn_for_room(self, room):
        data = self.game.world.data
        if room.get('enemy_spawned'):
            return ''
        room['enemy_spawned'] = True
        danger = int(room.get('danger', 0))
        if danger < 45 or self.rng.random() > 0.26:
            return ''
        templates = [
            ('одичавший мародёр', 42, 8, 18),
            ('агрессивный выживший', 36, 7, 16),
            ('одичавшая собака', 28, 6, 12),
        ]
        name, hp, damage, xp = random.choice(templates)
        enemy = {
            'id': f"enemy:{room['id']}",
            'name': name,
            'room_id': room['id'],
            'health': hp,
            'max_health': hp,
            'damage': damage,
            'xp': xp,
            'alive': True,
            'alert': False,
        }
        data.setdefault('enemies', []).append(enemy)
        return f'В этой зоне появляется {name}. Он замечает тебя.'

    def enemy_tick(self):
        active = self.active()
        if not active:
            return ''
        enemy = active[0]
        if enemy.get('alert') is False:
            enemy['alert'] = True
            return f"{enemy['name'].capitalize()} двигается в твою сторону."
        damage = int(enemy.get('damage', 5))
        self.game.world.data['health'] = max(0, self.game.world.data['health'] - damage)
        text = f"{enemy['name'].capitalize()} атакует тебя и наносит {damage} урона."
        if self.game.world.data['health'] <= 0:
            self.game.world.data['alive'] = False
            text += ' Ты погибаешь.'
        return text

    def attack(self, command='атаковать'):
        active = self.active()
        if not active:
            return 'Рядом нет противника.'
        enemy = active[0]
        damage = self._weapon_damage()
        enemy['health'] = max(0, enemy['health'] - damage)
        if damage > 0:
            self.game.world.data['flags']['last_combat'] = True
        text = f"Ты атакуешь {enemy['name']} и наносишь {damage} урона."
        if enemy['health'] <= 0:
            enemy['alive'] = False
            self.game.world.data['noise'] = min(100, int(self.game.world.data.get('noise', 0)) + 18)
            return text + f' {enemy["name"].capitalize()} падает.'
        enemy_damage = int(enemy.get('damage', 5))
        self.game.world.data['health'] = max(0, self.game.world.data['health'] - enemy_damage)
        text += f' В ответ он наносит {enemy_damage} урона.'
        if self.game.world.data['health'] <= 0:
            self.game.world.data['alive'] = False
            text += ' Ты погибаешь.'
        return text

    def defend(self):
        active = self.active()
        if not active:
            return 'Рядом нет противника.'
        enemy = active[0]
        damage = max(1, int(enemy.get('damage', 5)) // 2)
        self.game.world.data['health'] = max(0, self.game.world.data['health'] - damage)
        return f'Ты закрываешься от атаки. {enemy["name"].capitalize()} наносит {damage} урона.'

    def flee(self):
        active = self.active()
        if not active:
            return 'Угроза отсутствует.'
        enemy = active[0]
        if self.rng.random() < 0.65:
            enemy['alert'] = False
            return 'Ты резко отступаешь, увеличивая расстояние между собой и противником.'
        damage = int(enemy.get('damage', 5))
        self.game.world.data['health'] = max(0, self.game.world.data['health'] - damage)
        return f'Ты пытаешься убежать, но противник успевает ударить тебя на {damage} урона.'

    def _weapon_damage(self):
        inv = self.game.world.data.get('inventory_objects', [])
        best = 4
        for item in inv:
            name = str(item.get('name', '')).lower()
            props = [str(x).lower() for x in item.get('properties', [])]
            durability = int(item.get('durability', 50))
            if 'нож' in name or 'оруж' in ' '.join(props) or 'острый' in ' '.join(props):
                best = max(best, 16 if durability >= 50 else 10)
            elif any(x in name for x in ('лом', 'труба', 'молот', 'армат')):
                best = max(best, 12)
        return best
