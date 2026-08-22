# -*- coding: utf-8 -*-
class EventScheduler:
    def __init__(self, game):
        self.game = game

    def after_action(self, action_kind='action', moved=False):
        return self.game.events.tick(action_kind, moved)
