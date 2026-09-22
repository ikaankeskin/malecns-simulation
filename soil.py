"""Shared local nutrient budgets; engineered ecology, not calibrated biology."""
import math
import copy
import water

CELL_SIZE = 10.0
RECOVERY = 0.0008
CROP_COST = 0.6
COMPOST = 0.3


def create(rules, seed=0):
    if not rules.get('soil_limits', False):
        return None
    n = math.ceil(2 * rules['map_half'] / CELL_SIZE)
    result = dict(n=n, half=rules['map_half'], size=2 * rules['map_half'] / n,
                cells=[1.0] * (n*n), recovered=0.0, consumed=0.0, composted=0.0,
                recovery_per_tick=RECOVERY, crop_cost=CROP_COST, corpse_return=COMPOST)
    if rules.get('water', False):result['water']=water.create(result,seed)
    return result


def cell_index(soil, x, y):
    col = max(0, min(soil['n']-1, math.floor((x + soil['half']) / soil['size'])))
    row = max(0, min(soil['n']-1, math.floor((y + soil['half']) / soil['size'])))
    return row * soil['n'] + col


def growth_budget(soil, patches, growth, rules, tick=0):
    if soil is None:
        return {}
    water.advance(soil,tick,rules)
    for i, value in enumerate(soil['cells']):
        added = min(RECOVERY, 1-value)
        soil['cells'][i] += added
        soil['recovered'] += added
    demands = {}
    for patch in sorted(patches, key=lambda p:p['id']):
        if patch['stage'] != 'growing':
            continue
        index = cell_index(soil, patch['x'], patch['y'])
        demand = min(max(0, patch['timer']), growth) * CROP_COST / rules['grow_ticks']
        demands.setdefault(index, []).append((patch, demand))
    rates = {}
    for index, rows in demands.items():
        requested = sum(demand for _, demand in rows)
        fraction = min(1, soil['cells'][index] / requested) if requested else 1
        w=soil.get('water')
        if w is not None and requested:
            fraction=min(fraction,w['moisture'][index]/(requested*water.CROP_WATER/CROP_COST))
        if w is not None:
            drawn=requested*fraction*water.CROP_WATER/CROP_COST
            w['moisture'][index]=max(0,w['moisture'][index]-drawn);w['uptake']+=drawn
        spent = requested * fraction
        soil['cells'][index] = max(0, soil['cells'][index] - spent)
        soil['consumed'] += spent
        for patch, demand in rows:
            paid = demand * fraction
            rates[patch['id']] = min(max(0, patch['timer']), growth) if fraction == 1 else paid * rules['grow_ticks'] / CROP_COST
            patch['soil_uptake'] = patch.get('soil_uptake', 0) + paid
    return rates


def compost(soil, corpse, tick, events):
    index = cell_index(soil, corpse['x'], corpse['y'])
    gain = min(COMPOST, 1-soil['cells'][index])
    if gain <= 0:
        return False
    soil['cells'][index] += gain
    soil['composted'] += gain
    events.append(dict(tick=tick,kind='composted',agent=corpse['id'],cell=index,
                       x=corpse['x'],y=corpse['y'],nutrients=gain,
                       text=f'F{corpse["id"]} returned {gain:.3f} nutrients to soil cell {index}'))
    return True


def observe(soil, patches, tick):
    if soil is None:
        return
    for patch in patches:
        index = cell_index(soil, patch['x'], patch['y'])
        patch['soil_cell'] = index
        patch['fertility'] = soil['cells'][index]
        if 'water' in soil:patch['moisture']=soil['water']['moisture'][index]
        history = patch.setdefault('soil_history', [])
        if not history or tick-history[-1]['tick'] >= 100:
            history.append(dict(tick=tick,cell=index,fertility=soil['cells'][index]))
            del history[:-6]


def snapshot(soil, patches):
    if soil is None:
        return None
    occupied = {cell_index(soil,p['x'],p['y']) for p in patches}
    return dict(copy.deepcopy(soil), cells=list(soil['cells']),
                occupied_mean=sum(soil['cells'][i] for i in occupied)/max(1,len(occupied)),
                depleted_cells=sum(soil['cells'][i]<0.2 for i in occupied),
                occupied_cells=len(occupied))
