# -*- coding: utf-8 -*-
from .parser import normalize, direction, repeated_move, wants_take, wants_look, split_actions, looks_like_room_description

class ActionEngine:
    def __init__(self, game): self.game=game

    def inventory_text(self):
        items=self.game.world['inventory']
        return 'Инвентарь пуст.' if not items else 'В инвентаре: '+', '.join(items)+'.'

    def current_item(self,text):
        room=self.game.current_room(); t=normalize(text); best=None; score=0
        for item in room.get('items',[]):
            n=normalize(item.get('name',''))
            if n and n in t:return 'room',item
            words=[w for w in n.split() if len(w)>=3]; s=sum(1 for w in words if w in t)
            if s>score:best,score=item,s
        if best:return 'room',best
        best=None; score=0
        for obj in self.game.world.get('inventory_objects',[]):
            n=normalize(obj.get('name',''))
            if n and n in t:return 'inventory',obj
            words=[w for w in n.split() if len(w)>=3]; s=sum(1 for w in words if w in t)
            if s>score:best,score=obj,s
        return ('inventory',best) if best else (None,None)

    def object_target(self,text):
        room=self.game.current_room(); t=normalize(text); candidates=[]
        for obj in room.get('objects',[]):
            n=normalize(obj)
            if n in t:return obj
            words=[w for w in n.split() if len(w)>=3]; s=sum(1 for w in words if w in t)
            if s:candidates.append((s,obj))
        return max(candidates,key=lambda x:x[0])[1] if candidates else None

    def _move_and_describe(self,d):
        msg,room=self.game.move(d); return msg+'\n\n'+self.game.describe_room(room)

    def _apply_single(self,text):
        t=normalize(text)
        if t in ('выход','выйти из игры','закончить игру','завершить игру'):return '__EXIT__'
        if t in ('инвентарь','инвентай','открыть инвентарь','показать инвентарь') or 'что у меня' in t:return self.inventory_text()
        if t in ('помощь','список действий','показать помощь'):
            return 'Можно осматриваться, брать и использовать предметы, открывать двери, перемещаться, сражаться, защищаться, убегать, проверять ловушки, обезвреживать опасности и сохранять игру.'
        if looks_like_room_description(t):return 'Я не понял, какое действие выполнить.'
        if t in ('осмотреться','осмотрись','оглядеться','посмотреть вокруг','где я','осмотреть','посмотреться','осмотреть комнату'):
            return self.game.describe_current()
        if 'взять все' in t or 'забрать все' in t or 'подобрать все' in t or 'взять все предметы' in t:
            room=self.game.current_room(); results=[]
            for item in list(room.get('items',[])):
                if item.get('takeable',True):results.append(self.game.take_item(item))
            return ' '.join(results) if results else 'Здесь нет предметов, которые можно взять.'
        if ('откры' in t or 'отпер' in t) and 'двер' in t and any(x in t for x in ('идти','пойти','пройти','войти','выйти')):
            if self.game.is_start():
                opened=self.game.open_start_door()
                if 'заперта' in opened:return opened
                msg,room=self.game.move('north');return opened+'\n\n'+msg+'\n\n'+self.game.describe_room(room)
        if 'двер' in t and ('откры' in t or 'отпер' in t):
            if self.game.is_start():return self.game.open_start_door()
            obj=self.object_target(t)
            if obj:return self.game.object_interaction(t,obj)
        if t in ('выйти за дверь','пройти через дверь','пройти за дверь','войти в коридор'):
            if self.game.is_start() and self.game.world['rooms']['0_0_0'].get('special',{}).get('door_locked',False):return 'Ты не можешь пройти: металлическая дверь заперта.'
            return self._move_and_describe('north')
        d,count=repeated_move(t)
        if d:
            results=[];room=self.game.current_room()
            for _ in range(count):
                msg,room=self.game.move(d);results.append(msg)
            results.append(self.game.describe_room(room));return '\n\n'.join(results)
        d=direction(t)
        if d:return self._move_and_describe(d)
        source,item=self.current_item(t)
        if item:
            if wants_take(t):
                if source=='room':return self.game.take_item(item)
                return f"{item['name'].capitalize()} уже у тебя."
            if wants_look(t):return self.game.describe_item(item)
            if 'выбросить' in t or 'бросить' in t or 'оставить' in t:return self.game.drop_item(item)
            return self.game.item_interaction(t,item,source)
        obj=self.object_target(t)
        if obj:
            if wants_look(t):return f'Ты осматриваешь {obj}.'
            return self.game.object_interaction(t,obj)
        if 'двер' in t and any(x in t for x in ('подойти','выйти','пройти')):
            if self.game.is_start():
                if 'выйти' in t or 'пройти' in t:
                    if self.game.world['rooms']['0_0_0'].get('special',{}).get('door_locked',False):return 'Ты не можешь пройти: металлическая дверь заперта.'
                    return self._move_and_describe('north')
                return 'Ты подходишь к металлической двери.'
        return None

    def apply(self,text):
        parts=split_actions(text)
        if len(parts)>1:
            results=[]
            for part in parts:
                result=self._apply_single(part)
                if result=='__EXIT__':return result
                if result is not None:results.append(result)
            return '\n\n'.join(results) if results else None
        return self._apply_single(normalize(text))
