# -*- coding: utf-8 -*-
class ThreatSystem:
    def __init__(self, game):
        self.game = game

    def status(self):
        enemies = self.game.combat.active()
        if not enemies:
            return 'Непосредственной угрозы рядом нет.'
        return 'Угроза: ' + ', '.join(e['name'] for e in enemies) + '.'
