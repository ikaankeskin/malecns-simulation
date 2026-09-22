"""Engineered seed dispersal and persistent gardens; no biological claim."""
import math

DEFAULTS = {'gardening': False}
PLANT_COST = 0.08
SEED_LIFE = 600
MIN_TRAVEL = 3
MIN_SPACING = 2
MAX_GARDENS = 64


def on_meal(agent, patch, agents, tick, rules):
    if not rules['gardening']:
        return
    patch['harvests'] = patch.get('harvests', 0) + 1
    patch['recent_eaters'] = (patch.get('recent_eaters', []) + [{'agent': agent['id'], 'tick': tick}])[-6:]
    planter = patch.get('planter')
    if planter is not None:
        by_id = {a['id']: a for a in agents}
        pending = list(agent.get('parents') or [])
        seen = set()
        while pending:
            parent = pending.pop()
            if parent in seen:
                continue
            seen.add(parent)
            pending.extend(by_id.get(parent, {}).get('parents') or [])
        if planter in seen:
            patch['descendant_meals'] = patch.get('descendant_meals', 0) + 1
        if not by_id.get(planter, {}).get('alive', False):
            patch['posthumous_meals'] = patch.get('posthumous_meals', 0) + 1
    if not agent.get('carried_seed'):
        agent['carried_seed'] = {'source_patch': patch['id'], 'x': patch['x'], 'y': patch['y'],
                                 'tick': tick, 'until': tick + SEED_LIFE,
                                 'root_patch': patch.get('root_patch', patch['id']),
                                 'plant_generation': patch.get('plant_generation', 0) + 1}


def plant_seeds(agents, patches, tick, rules, events):
    if not rules['gardening']:
        return
    for agent in sorted(agents, key=lambda a: a['id']):
        seed = agent.get('carried_seed')
        if not seed:
            continue
        if not agent['alive'] or tick >= seed['until']:
            agent['carried_seed'] = None
            continue
        if tick - seed['tick'] < 20 or agent['energy'] < 0.8:
            continue
        if math.hypot(agent['x'] - seed['x'], agent['y'] - seed['y']) < MIN_TRAVEL:
            continue
        if any(math.hypot(agent['x'] - p['x'], agent['y'] - p['y']) < MIN_SPACING for p in patches):
            continue
        if sum(p.get('planter') is not None for p in patches) >= MAX_GARDENS:
            continue
        if abs(agent['x']) > rules['map_half'] or abs(agent['y']) > rules['map_half']:
            continue
        patch = {'id': max((p['id'] for p in patches), default=-1) + 1,
                 'x': agent['x'], 'y': agent['y'], 'stage': 'seed', 'timer': rules['seed_ticks'],
                 'nutrition': 1.0, 'consumed_by': None, 'planter': agent['id'],
                 'planted_tick': tick, 'planter_generation': agent.get('generation', 0),
                 'parent_patch': seed['source_patch'], 'root_patch': seed['root_patch'],
                 'plant_generation': seed['plant_generation'], 'harvests': 0,
                 'descendant_meals': 0, 'posthumous_meals': 0, 'recent_eaters': []}
        patches.append(patch)
        agent['energy'] -= PLANT_COST
        agent['carried_seed'] = None
        agent['planted'] = agent.get('planted', 0) + 1
        events.append({'tick': tick, 'kind': 'planted', 'agent': agent['id'], 'patch': patch['id'],
                       'x': patch['x'], 'y': patch['y'],
                       'text': f'F{agent["id"]} planted garden P{patch["id"]} from P{patch["parent_patch"]}'})


def totals(patches):
    gardens = [p for p in patches if p.get('planter') is not None]
    return {'planted': len(gardens), 'mature': sum(p['stage'] == 'mature' for p in gardens),
            **{key: sum(p.get(key, 0) for p in gardens)
               for key in ('harvests', 'descendant_meals', 'posthumous_meals')}}
