# -*- coding: utf-8 -*-
class Dialogue:
    def __init__(self): self.messages=[]
    def add(self, role, text): self.messages.append({'role':role,'text':text})
