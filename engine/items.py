# -*- coding: utf-8 -*-
from copy import deepcopy

def make_item(name, description='', takeable=True, state='обычное состояние', properties=None, quantity=1, durability=100):
    return {'id': f'item:{name}', 'name':name, 'description':description, 'takeable':bool(takeable), 'state':state, 'properties':list(properties or []), 'quantity':max(1,int(quantity)), 'durability':max(0,min(100,int(durability)))}

def find_item(items, text):
    t=text.lower(); candidates=[]
    for item in items:
        n=item.get('name','').lower()
        if n and n in t: return item
        words=[w for w in n.split() if len(w)>=3]
        score=sum(w in t for w in words)
        if score: candidates.append((score,item))
    return max(candidates,key=lambda x:x[0])[1] if candidates else None

def take_item(room, item, inventory_objects, inventory, memory):
    if not item.get('takeable',True): return f"Ты не можешь взять {item['name']}."
    if item not in room['items']: return f"{item['name'].capitalize()} уже у тебя."
    room['items'].remove(item)
    obj=deepcopy(item); inventory_objects.append(obj); inventory.append(item['name']); memory.add(f"Игрок взял {item['name']}.")
    return f"Ты берёшь {item['name']}."
