# -*- coding: utf-8 -*-
class Memory:
    def __init__(self, events=None): self.events = list(events or [])
    def add(self, text): self.events.append(text)
    def recent(self, n=30): return self.events[-n:]
