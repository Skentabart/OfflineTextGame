# -*- coding: utf-8 -*-
class InventorySystem:
    def __init__(self, game):
        self.game = game

    def text(self):
        items = self.game.world.data.get('inventory', [])
        return 'Инвентарь пуст.' if not items else 'В инвентаре: ' + ', '.join(items) + '.'
