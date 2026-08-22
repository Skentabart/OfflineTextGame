# -*- coding: utf-8 -*-
from .rules import add_coord, opposite

def room_id(x,y,z=0): return f'{x}_{y}_{z}'

def _name(value):
    if isinstance(value, dict):
        return str(value.get('name', value.get('title', 'неизвестный объект'))).strip()
    return str(value).strip()

def describe(room):
    out=[]
    if room.get('title'): out.append(room['title'])
    if room.get('description'): out.append(room['description'])
    if room.get('atmosphere'): out.append(room['atmosphere'])
    objects=[_name(v) for v in room.get('objects',[]) if _name(v)]
    if objects: out.append('В помещении находятся: '+', '.join(objects)+'.')
    items=[]
    for i in room.get('items',[]):
        if isinstance(i,dict): items.append(_name(i))
        elif i: items.append(str(i))
    if items: out.append('Здесь можно увидеть: '+', '.join(items)+'.')
    labels={'north':'север','south':'юг','east':'восток','west':'запад'}
    exits=[labels[d] for d,v in room.get('exits',{}).items() if v and d in labels]
    if exits: out.append('Выходы: '+', '.join(exits)+'.')
    return '\n'.join(out)

def link(room, rooms):
    for d,target in room.get('exits',{}).items():
        if not target: continue
        nx,ny=add_coord(room['x'],room['y'],d); rid=room_id(nx,ny,room['z'])
        if rid in rooms: rooms[rid]['exits'][opposite(d)]=room['id']
