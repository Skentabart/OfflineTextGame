# -*- coding: utf-8 -*-
from .world import World
from .actions import ActionEngine
from .rooms import room_id, describe
from .rules import add_coord, opposite, direction_label
from .parser import normalize
from .events import EventSystem
from .combat import CombatSystem
from .hazards import HazardSystem
from .threats import ThreatSystem
from .physics import PhysicsSystem
from .scheduler import EventScheduler
from .inventory import InventorySystem

class GameEngine:
    def __init__(self, config, qwen, room_generator, interaction_ai, narrator):
        self.config = config
        self.qwen = qwen
        self.room_generator = room_generator
        self.interaction_ai = interaction_ai
        self.narrator = narrator
        self.world = World(config.get('world_seed','OFFLINE_GAME_V30'))
        self.world.set_initial()
        self.context = self.world.context
        self.memory = self.world.memory
        self.actions = ActionEngine(self)
        self.events = EventSystem(self)
        self.combat = CombatSystem(self)
        self.hazards = HazardSystem(self)
        self.threats = ThreatSystem(self)
        self.physics = PhysicsSystem(self)
        self.scheduler = EventScheduler(self)
        self.inventory = InventorySystem(self)

    def current_room(self):
        return self.world.room()

    def describe_room(self, room=None):
        return describe(room or self.current_room())

    def describe_current(self):
        return self.describe_room()

    def describe_item(self, item):
        p = item.get('properties', [])
        text = f"{item['name'].capitalize()}. {item.get('description','')}"
        if item.get('state'):
            text += f" Состояние: {item['state']}."
        if p:
            text += ' Свойства: ' + ', '.join(p) + '.'
        self.context.remember(target=item['name'], target_type='item', action='look')
        return text.strip()

    def is_start(self):
        return self.world.location == {'x':0,'y':0,'z':0}

    def open_start_door(self):
        room = self.world.data['rooms']['0_0_0']
        if not room['special'].get('door_locked', False):
            self.context.remember(target='металлическая дверь', target_type='object', action='open')
            return 'Металлическая дверь уже открыта.'
        if not any('ключ' in normalize(x) for x in self.world.data['inventory']):
            return 'Металлическая дверь заперта. У тебя нет ключа.'
        room['special']['door_locked'] = False
        room['exits']['north'] = '0_1_0'
        self.world.data['flags']['door_open'] = True
        self.memory.add('Игрок открыл металлическую дверь.')
        self.context.remember(target='металлическая дверь', target_type='object', action='open')
        return 'Ты вставляешь ржавый ключ в замок. Замок щёлкает, и металлическая дверь открывается.'

    def generate_room(self, x, y, z):
        rid = room_id(x,y,z)
        if rid in self.world.data['rooms']:
            return self.world.data['rooms'][rid]
        room = self.room_generator.generate(self.world.data, x, y, z, self.qwen)
        self.world.data['rooms'][rid] = room
        for d, target in room.get('exits', {}).items():
            if target and target in self.world.data['rooms']:
                self.world.data['rooms'][target]['exits'][opposite(d)] = rid
        return room

    def move(self, direction):
        r = self.current_room()
        x = self.world.location['x']; y = self.world.location['y']; z = self.world.location['z']
        nx, ny = add_coord(x,y,direction)
        rid = room_id(nx,ny,z)
        if self.is_start() and direction == 'north' and r.get('special',{}).get('door_locked',False):
            return 'Ты не можешь пройти: металлическая дверь заперта.', r
        r['exits'][direction] = rid
        target = self.generate_room(nx,ny,z) if rid not in self.world.data['rooms'] else self.world.data['rooms'][rid]
        self.world.data['location'] = {'x':nx,'y':ny,'z':z}
        target['exits'][opposite(direction)] = r['id']
        self.context.remember(location=dict(self.world.data['location']))
        spawn_text = self.combat.spawn_for_room(target)
        base = f'Ты направляешься на {direction_label(direction)}.'
        return base + (('\n\n' + spawn_text) if spawn_text else ''), target

    def take_item(self, item):
        if not item.get('takeable', True):
            return f"Ты не можешь взять {item['name']}."
        room = self.current_room()
        if item not in room.get('items', []):
            return f"{item['name'].capitalize()} уже находится у тебя."
        room['items'].remove(item)
        obj = dict(item)
        self.world.data['inventory_objects'].append(obj)
        self.world.data['inventory'].append(item['name'])
        self.memory.add(f"Игрок взял {item['name']}.")
        self.context.remember(target=item['name'], target_type='item', action='take')
        return f"Ты берёшь {item['name']}."

    def drop_item(self, item):
        name = item['name']
        if name in self.world.data['inventory']:
            self.world.data['inventory'].remove(name)
        try:self.world.data['inventory_objects'].remove(item)
        except ValueError:pass
        self.current_room()['items'].append(dict(item))
        self.context.remember(target=name, target_type='item', action='drop')
        return f'Ты оставляешь {name}.'

    def item_interaction(self, command, item, source):
        self.context.remember(target=item['name'], target_type='item', action=command)
        res = self.interaction_ai.item_action(command, item, source, self.world.data, self.qwen)
        if res.get('new_state'):
            item['state'] = res['new_state']
        item['durability'] = max(0, min(100, int(item.get('durability',100)) + int(res.get('durability_delta',0))))
        if res.get('remove_item'):
            if source == 'room':
                try:self.current_room()['items'].remove(item)
                except ValueError:pass
            else:
                name = item['name']
                if name in self.world.data['inventory']:
                    self.world.data['inventory'].remove(name)
                try:self.world.data['inventory_objects'].remove(item)
                except ValueError:pass
        return res.get('message') or f"Ты взаимодействуешь с {item['name']}."

    def object_interaction(self, command, obj):
        self.context.remember(target=obj, target_type='object', action=command)
        return self.interaction_ai.object_action(command, obj, self.current_room(), self.qwen)

    def command(self, text):
        resolved = self.context.resolve_pronoun(normalize(text))
        self.context.remember(command=resolved)
        if not self.world.data.get('alive', True):
            return 'Ты больше не можешь действовать. Игра окончена.'
        action_kind = self.physics.apply(resolved)
        direct = self.actions.apply(resolved)
        moved = any(x in resolved for x in ('север','юг','восток','запад')) and any(x in resolved for x in ('идти','пойти','войти','выйти','пройти'))
        if direct == '__EXIT__':
            return direct
        result = direct
        if result is None:
            low = normalize(resolved)
            if low in ('атаковать','атаковать врага','напасть','ударить врага'):
                result = self.combat.attack(resolved); action_kind='combat'
            elif low in ('защищаться','защититься','прикрыться','блокировать'):
                result = self.combat.defend(); action_kind='combat'
            elif low in ('убежать','бежать','отступить'):
                result = self.combat.flee(); action_kind='combat'
            elif 'обезвред' in low:
                result = self.hazards.disarm(); action_kind='force'
            elif any(x in low for x in ('обнаружить ловушку','найти ловушку','проверить опасность','осмотреть опасность')):
                result = self.hazards.inspect(); action_kind='action'
            elif low in ('угроза','статус угрозы'):
                result = self.threats.status(); action_kind='action'
            else:
                result = self.interaction_ai.free_action(resolved, self.current_room(), self.world.data, self.qwen)
        if result == '__EXIT__':
            return result
        event_text = self.scheduler.after_action(action_kind, moved=moved)
        self.context.remember(result=result)
        self.world.data['events'] = self.memory.events
        if event_text:
            result = result + '\n\n' + event_text
        if not self.world.data.get('alive', True):
            result += '\n\nТы погиб. Игра окончена.'
        return self.narrator.clean(result)
