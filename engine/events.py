# -*- coding: utf-8 -*-
import random

class EventSystem:
    def __init__(self, game):
        self.game = game
        self.rng = random.Random()

    def tick(self, action_kind='action', moved=False):
        world = self.game.world.data
        room = self.game.current_room()
        world['game_time'] = int(world.get('game_time', 0)) + 1
        self._ambient(room)
        results = []
        hazard = self._hazard(room, moved)
        if hazard:
            results.append(hazard)
        threat = self.game.combat.enemy_tick()
        if threat:
            results.append(threat)
        event = self._dynamic_event(room, action_kind, moved)
        if event:
            results.append(event)
        return '\n\n'.join(results)

    def _ambient(self, room):
        flags = room.setdefault('flags', {})
        if self.rng.random() < 0.18:
            ambient = random.choice([
                'Где-то в глубине здания раздаётся короткий металлический удар.',
                'С потолка падают несколько капель, и звук долго гуляет по пустому помещению.',
                'Воздух на мгновение становится тяжелее, а затем всё снова стихает.',
                'Где-то за стеной слышится далёкий скрежет.'
            ])
            flags['last_ambient'] = ambient

    def _hazard(self, room, moved):
        hazard = room.get('hazard')
        if not hazard or hazard.get('triggered') or hazard.get('disabled'):
            return ''
        chance = float(hazard.get('chance', 0.0))
        if not moved:
            chance *= 0.35
        if self.rng.random() > chance:
            return ''
        hazard['triggered'] = True
        damage = int(hazard.get('damage', 5))
        self.game.world.data['health'] = max(0, self.game.world.data['health'] - damage)
        text = hazard.get('message', 'Срабатывает скрытая опасность.')
        if damage:
            text += f' Ты получаешь {damage} урона.'
        if self.game.world.data['health'] <= 0:
            self.game.world.data['alive'] = False
            text += ' Ты погибаешь.'
        return text

    def _dynamic_event(self, room, action_kind, moved):
        danger = int(room.get('danger', 0))
        if danger <= 0:
            return ''
        chance = 0.0
        if moved:
            chance += min(0.14, danger / 800)
        elif action_kind in ('combat', 'noise', 'force'):
            chance += min(0.18, danger / 500)
        if self.rng.random() > chance:
            return ''
        choices = [
            'Слева раздаётся резкий шум, будто что-то тяжёлое сдвинулось.',
            'Свет на мгновение становится слабее, и в темноте слышится движение.',
            'Старая конструкция рядом содрогается от далёкого удара.',
            'Из соседнего помещения доносится быстрый металлический стук.'
        ]
        return random.choice(choices)
