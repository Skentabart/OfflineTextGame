# -*- coding: utf-8 -*-
from engine.rooms import room_id
from engine.rules import add_coord

class RoomGenerator:
    def generate(self,world,x,y,z,qwen):
        seed=f"{world['world_seed']}|{x}|{y}|{z}"
        system=('Ты генератор одной реалистичной зоны постапокалиптической игры. Верни только короткий JSON без markdown. Не создавай персонажей или монстров. Создай уникальную локацию, 2-6 объектов, 1-4 предмета и 2-4 выхода. Каждый предмет: name, description, takeable, state, properties, quantity, durability. Добавь danger от 0 до 100. Иногда добавь hazard с description, damage и chance. Не повторяй предыдущие зоны.')
        user=f'Координаты X={x} Y={y} Z={z}. Seed={seed}. Придумай уникальное место: тоннель, склад, лестничную клетку, улицу, подстанцию, мастерскую, подземный переход, диспетчерскую или другое правдоподобное место. JSON должен быть коротким.'
        for attempt in range(3):
            raw=qwen.chat(system,user+(' Ответ максимально короткий.' if attempt else ''),max_tokens=220,temperature=.45,timeout=12)
            data=qwen.parse_json(raw)
            if data:
                room=self.normalize(data,x,y,z)
                if room: return room
        return self.fallback(x,y,z)

    def normalize(self,d,x,y,z):
        if not isinstance(d, dict):
            return None

        title=str(d.get('title','Неизведанная область')).strip()
        desc=str(d.get('description','Заброшенное помещение.')).strip()
        if not title or not desc:
            return None

        objects=[]
        items=[]
        seen_objects=set()
        seen_items=set()

        def add_item(raw, index):
            if isinstance(raw, str):
                raw={'name': raw}
            if not isinstance(raw, dict):
                return
            name=str(raw.get('name', raw.get('title', ''))).strip()
            if not name:
                return
            key=name.lower()
            if key in seen_items:
                return
            seen_items.add(key)
            props=raw.get('properties', [])
            if not isinstance(props, list):
                props=[props]
            clean_props=[str(v).strip() for v in props if str(v).strip()]
            try: qty=max(1,min(20,int(raw.get('quantity',1) or 1)))
            except Exception: qty=1
            try: dur=max(0,min(100,int(raw.get('durability',100) or 100)))
            except Exception: dur=100
            items.append({
                'id':str(raw.get('id',f'item:{x}:{y}:{z}:{index}:{len(items)}')),
                'name':name,
                'description':str(raw.get('description','')).strip(),
                'takeable':bool(raw.get('takeable',True)),
                'state':str(raw.get('state','обычное состояние')).strip(),
                'properties':clean_props,
                'quantity':qty,
                'durability':dur
            })

        # Любой словарь в objects с именем считаем интерактивным предметом.
        # Это защищает от типичной ошибки маленькой Qwen, когда item попадает в objects.
        raw_objects=d.get('objects',[])
        if isinstance(raw_objects,list):
            for idx,value in enumerate(raw_objects):
                if isinstance(value,dict):
                    if value.get('name') or value.get('title'):
                        add_item(value,idx)
                    continue
                name=str(value).strip()
                if name and name.lower() not in seen_objects:
                    seen_objects.add(name.lower())
                    objects.append(name)

        raw_items=d.get('items',[])
        if isinstance(raw_items,list):
            for idx,value in enumerate(raw_items):
                add_item(value,idx)

        raw_exits=d.get('exits',[])
        room={
            'id':room_id(x,y,z),'x':x,'y':y,'z':z,
            'title':title,'description':desc,
            'atmosphere':str(d.get('atmosphere','Воздух холодный, влажный и тяжёлый.')).strip(),
            'objects':objects,'items':items,
            'exits':{'north':None,'south':None,'east':None,'west':None},
            'special':{},
            'danger':max(0,min(100,int(d.get('danger',20) or 20))),
            'hazard':d.get('hazard') if isinstance(d.get('hazard'),dict) else None
        }

        if isinstance(raw_exits,list):
            for direction in raw_exits:
                if direction in room['exits']:
                    nx,ny=add_coord(x,y,direction)
                    room['exits'][direction]=room_id(nx,ny,z)

        if not any(room['exits'].values()):
            room['exits']['north']=room_id(x,y+1,z)
            room['exits']['south']=room_id(x,y-1,z)

        if room['danger']>60 and not room['hazard']:
            room['hazard']={'description':'участок пола выглядит ненадёжно','damage':4,'chance':0.12,'triggered':False,'disabled':False,'discovered':False}

        return room

    def fallback(self,x,y,z):
        presets=[
            ('Заброшенный технический коридор','Узкий коридор старой инфраструктуры уходит в полумрак.',['кабельный лоток','ржавый вентиль'],['обломок изолятора','старый металлический хомут'],55),
            ('Старая диспетчерская','Пустое помещение с остатками старого оборудования.',['щит управления','пыльный стеллаж'],['катушка провода','сломанный переключатель'],65),
            ('Подземный переход','Низкий бетонный переход покрыт следами сырости.',['бетонная опора','металлическое ограждение'],['ржавый болт','обрывок сигнальной ленты'],35),
            ('Технический склад','Заброшенное помещение с остатками складского оборудования.',['металлический стеллаж','сломанный контейнер'],['ремонтный инструмент','пластиковая ёмкость'],45),
            ('Старая служебная комната','Небольшая комната с потемневшими стенами и следами длительного запустения.',['деревянная дверь','настенная полка'],['лист бумаги','старая перчатка'],30),
            ('Заброшенная подстанция','Небольшое помещение с остатками электрооборудования.',['щитовая панель','силовой кабель'],['предохранитель','медная клемма'],70),
        ]
        idx=abs(x*31+y*17+z*7)%len(presets);title,desc,objects,names,danger=presets[idx]
        items=[]
        for i,name in enumerate(names):items.append({'id':f'fallback:{x}:{y}:{z}:{i}','name':name,'description':f'{name.capitalize()} сохранился здесь, несмотря на годы запустения.','takeable':True,'state':'изношенное','properties':['физический предмет'],'quantity':1,'durability':50+(i*17)%50})
        hazard=None
        if danger>60:hazard={'description':'повреждённый участок оборудования','damage':6,'chance':.14,'triggered':False,'disabled':False,'discovered':False}
        return {'id':room_id(x,y,z),'x':x,'y':y,'z':z,'title':title,'description':desc,'atmosphere':'Воздух холодный, влажный и тяжёлый.','objects':objects,'items':items,'exits':{'north':room_id(x,y+1,z),'south':room_id(x,y-1,z),'east':room_id(x+1,y,z),'west':room_id(x-1,y,z)},'special':{},'danger':danger,'hazard':hazard}
