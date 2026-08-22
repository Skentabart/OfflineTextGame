# -*- coding: utf-8 -*-
from .rooms import room_id
from .context import Context
from .memory import Memory

class World:
    def __init__(self, seed='OFFLINE_GAME_V30'):
        self.data={
            'world_seed':seed,'location':{'x':0,'y':0,'z':0},'rooms':{},
            'inventory':[],'inventory_objects':[],'health':100,'alive':True,
            'events':[],'quests':[],'flags':{},'game_time':0,'noise':0,'enemies':[]
        }
        self.context=Context(); self.memory=Memory(self.data['events'])

    def __getitem__(self,key): return self.data[key]
    def get(self,key,default=None): return self.data.get(key,default)
    @property
    def location(self): return self.data['location']
    def room(self):
        l=self.location
        return self.data['rooms'][room_id(l['x'],l['y'],l['z'])]
    def set_initial(self):
        self.data['rooms']['0_0_0']={
            'id':'0_0_0','x':0,'y':0,'z':0,
            'title':'Большой зал старой станции',
            'description':'Большой зал заброшенной станции. За грязными окнами льёт холодный дождь. Пыль покрывает пол.',
            'atmosphere':'В помещении пахнет сыростью, ржавчиной и старым машинным маслом.',
            'objects':['металлическая дверь','старый стол','грязное окно'],
            'items':[
                {'id':'i_lamp','name':'старый фонарь','description':'Старый ручной фонарь с потёртым корпусом.','takeable':True,'state':'выключен','properties':['ручной','металлический'],'quantity':1,'durability':70},
                {'id':'i_knife','name':'старый нож','description':'Старый нож с потёртой рукоятью.','takeable':True,'state':'исправен','properties':['острый','металлический'],'quantity':1,'durability':55},
                {'id':'i_key','name':'ржавый ключ','description':'Ржавый металлический ключ.','takeable':True,'state':'ржавый','properties':['металлический','маленький'],'quantity':1,'durability':80},
                {'id':'i_bottle','name':'бутылка','description':'Старая стеклянная бутылка.','takeable':True,'state':'целая','properties':['стеклянная','хрупкая'],'quantity':1,'durability':30}
            ],
            'exits':{'north':'0_1_0','south':None,'east':None,'west':None},
            'special':{'door_locked':True},
            'danger':5,'hazard':None
        }

    def to_dict(self):
        self.data['events']=self.memory.events
        return self.data
    def from_dict(self,data):
        self.data=data
        self.memory=Memory(self.data.get('events',[]))
        self.context=Context()
        self.data.setdefault('noise',0)
        self.data.setdefault('enemies',[])
        self.data.setdefault('alive',True)
    def room_id(self):
        return room_id(self.location['x'],self.location['y'],self.location['z'])
