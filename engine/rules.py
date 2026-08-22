# -*- coding: utf-8 -*-
DIRECTIONS={'north':'север','south':'юг','east':'восток','west':'запад'}
OPPOSITE={'north':'south','south':'north','east':'west','west':'east'}
MOVE_DELTAS={'north':(0,1),'south':(0,-1),'east':(1,0),'west':(-1,0)}
def direction_label(d):return DIRECTIONS.get(d,d)
def opposite(d):return OPPOSITE[d]
def add_coord(x,y,d):dx,dy=MOVE_DELTAS[d];return x+dx,y+dy
