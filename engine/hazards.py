# -*- coding: utf-8 -*-
class HazardSystem:
    def __init__(self, game):
        self.game = game

    def inspect(self):
        room = self.game.current_room()
        hazard = room.get('hazard')
        if not hazard or hazard.get('disabled'):
            return 'Явной опасности не видно.'
        hazard['discovered'] = True
        return 'Ты замечаешь возможную опасность: ' + str(hazard.get('description', 'опасный участок')) + '.'

    def disarm(self):
        room = self.game.current_room()
        hazard = room.get('hazard')
        if not hazard or hazard.get('disabled'):
            return 'Здесь нет заметной ловушки.'
        if not hazard.get('discovered'):
            return 'Ты не видишь механизм ловушки.'
        hazard['disabled'] = True
        return 'Опасность обезврежена.'
