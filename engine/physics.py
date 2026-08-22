# -*- coding: utf-8 -*-
class PhysicsSystem:
    def __init__(self, game):
        self.game = game

    def noise(self, amount=0):
        world = self.game.world.data
        world['noise'] = max(0, min(100, int(world.get('noise', 0)) + int(amount)))

    def apply(self, command):
        t = command.lower()
        if any(x in t for x in ('удар', 'слом', 'разбить', 'выстрел', 'крич', 'громко')):
            self.noise(15)
            return 'noise'
        if any(x in t for x in ('открыть', 'закрыть', 'потянуть', 'повернуть', 'нажать')):
            self.noise(4)
            return 'force'
        return 'action'
