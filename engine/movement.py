# -*- coding: utf-8 -*-
from .rules import add_coord, opposite, direction_label
from .rooms import room_id

def move(game,direction):
    room=game.current_room(); loc=game.world['location']; nx,ny=add_coord(loc['x'],loc['y'],direction); z=loc['z']; target=room_id(nx,ny,z)
    if loc['x']==0 and loc['y']==0 and loc['z']==0 and direction=='north' and room.get('special',{}).get('door_locked',False):
        return 'Ты не можешь пройти: металлическая дверь заперта.', room
    room['exits'][direction]=target
    if target not in game.world['rooms']:
        target_room=game.generate_room(nx,ny,z)
    else: target_room=game.world['rooms'][target]
    game.world['location']={'x':nx,'y':ny,'z':z}; target_room['exits'][opposite(direction)]=room['id']; game.world['game_time']+=1; game.memory.add('Переход: '+direction_label(direction)+'.')
    game.context.remember(location=dict(game.world['location']))
    return f'Ты направляешься на {direction_label(direction)}.', target_room
