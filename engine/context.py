# -*- coding: utf-8 -*-
import re

class Context:
    def __init__(self):
        self.last_target = None
        self.last_target_type = None
        self.last_action = None
        self.last_command = ''
        self.last_result = ''
        self.last_location = None

    def remember(self, target=None, target_type=None, action=None, command=None, result=None, location=None):
        if target is not None:
            self.last_target = target
        if target_type is not None:
            self.last_target_type = target_type
        if action is not None:
            self.last_action = action
        if command is not None:
            self.last_command = command
        if result is not None:
            self.last_result = result
        if location is not None:
            self.last_location = location

    def resolve_pronoun(self, text):
        if not self.last_target:
            return text
        target = self.last_target
        out = str(text)
        patterns = [
            (r'\bего\b', target),
            (r'\bее\b', target),
            (r'\bему\b', target),
            (r'\bей\b', target),
            (r'\bим\b', target),
            (r'\bэтот предмет\b', target),
            (r'\bэтот объект\b', target),
            (r'\bэта вещь\b', target),
            (r'\bданный предмет\b', target),
            (r'\bэтот\b', target),
            (r'\bэта\b', target),
            (r'\bэто\b', target),
        ]
        for pattern, replacement in patterns:
            out = re.sub(pattern, replacement, out, flags=re.IGNORECASE)
        return out
