# -*- coding: utf-8 -*-
class ActionInterpreter:
    def classify(self, text):
        t = text.lower()
        if any(x in t for x in ('атаковать', 'ударить', 'зарезать', 'напасть')):
            return 'combat'
        if any(x in t for x in ('защит', 'прикрыться', 'блок')):
            return 'defend'
        if any(x in t for x in ('убежать', 'бежать', 'отступить')):
            return 'flee'
        if any(x in t for x in ('обезвред', 'обезопас')):
            return 'disarm'
        if any(x in t for x in ('ловуш', 'опасност')):
            return 'hazard'
        return 'action'
