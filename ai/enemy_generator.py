# -*- coding: utf-8 -*-
class EnemyGenerator:
    def generate_hint(self, room):
        danger = int(room.get('danger', 0))
        if danger < 45:
            return ''
        return 'Высокая вероятность угрозы.'
