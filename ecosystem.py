"""Persistent multi-agent ecosystem. World rules are simulation abstractions."""
import json
import math
import random
import social
import copy
from pathlib import Path
from sim import Circuit, integrate_motion, nearest_point, sensory_drives, validate_decoder, validate_graph

DEFAULTS = {
    'agents': 8,
    'patches': 8,
    'map_half': 20.0,
    'energy_start': 1.0,
    'energy_max': 2.0,
    'base_drain': 0.0012,
    'move_cost': 0.003,
    'meal': 0.55,
    'eat_radius': 0.55,
    'sense_range': 24.0,
    'max_age': 520,
    'seed_ticks': 12,
    'grow_ticks': 40,
    'cooldown_ticks': 50,
    'corpse_ticks': 180,
    'seasons': True,
    'season_length': 400,
    'scavenging': True,
    'hazards': True,
    'hazard_count': 3,
    'hazard_radius': 3.5,
    'hazard_drain': 0.02,
    'gifts': False,
    'gift_amount': 0.15,
    'gift_keep': 0.10,
    'gift_range': 4.0,
    'gift_cooldown': 80,
    'gift_chance': 0.25,
    'gift_follow': 100,
    'predation': False,
    'attack_range': 2.0,
    'attack_cost': 0.08,
    'attack_damage': 0.45,
    'attack_cooldown': 40,
    'attack_chance': 0.35,
    'attack_floor': 0.5,
    'frozen_genes': [],
    'lifetime_learning': True,
    'scavenge_below': 1.1,
    'corpse_meal': 0.35,
    'compost_radius': 5.0,
    'compost_boost': 12.0,
    'max_population': 48,
    'mate_radius': 6.0,
    'min_repro_age': 36,
    'min_repro_energy': 1.05,
    'repro_cost': 0.35,
    'repro_cooldown': 40,
    'offspring_energy': 0.8,
    'food_rate': 1.0,
    'aging_rate': 1.0,
    'repro_rate': 1.2,
    'mutation_rate': 0.9,
    'mutation_sigma': 0.14,
    'meal_life': 90,
    'meal_life_cap': 900,
    'record_every': 1,
}

DEFAULTS.update(social.DEFAULTS)

INT_KEYS = ('agents', 'patches', 'max_age', 'seed_ticks', 'grow_ticks', 'cooldown_ticks',
            'corpse_ticks', 'max_population', 'min_repro_age', 'repro_cooldown',
            'meal_life', 'meal_life_cap', 'record_every', 'season_length', 'signal_ticks', 'signal_cooldown', 'memory_ticks',
            'hazard_count', 'gift_cooldown', 'gift_follow', 'attack_cooldown')
RATE_KEYS = ('food_rate', 'aging_rate', 'repro_rate', 'mutation_rate', 'mutation_sigma')

# Relative body/decoder multipliers. Topology is not in the genome.
BASE_GENOME = {
    'turn_gain': 1.0,
    'sensory_gain': 1.0,
    'metabolism': 1.0,
    'speed': 1.0,
    'lifespan': 1.0,
    'fertility': 1.0,
    'signalling': 0.5,
    'responsiveness': 0.5,
    'spot': 0.0,
    'echo': 0.0,
    'drift': 0.0,
    'caution': 1.0,
    'generosity': 1.0,
    'aggression': 1.0,
}
GENE_BOUNDS = {
    'turn_gain': (0.45, 2.0),
    'sensory_gain': (0.45, 2.2),
    'metabolism': (0.5, 1.8),
    'speed': (0.55, 1.9),
    'lifespan': (0.65, 1.9),
    'fertility': (0.6, 2.2),
    'signalling': (0.0, 1.0),
    'responsiveness': (0.0, 1.0),
    'spot': (0.0, 1.0),
    'echo': (0.0, 1.0),
    'drift': (0.0, 1.0),
    'caution': (0.0, 2.0),
    'generosity': (0.0, 2.0),
    'aggression': (0.0, 2.0),
}
ADDITIVE_GENES = ('spot', 'echo', 'drift', 'signalling', 'responsiveness', 'caution', 'generosity', 'aggression')
MUTATION_LABELS = {
    'speed': ('speed boost', 'sluggish'),
    'lifespan': ('long life', 'short life'),
    'fertility': ('litter +1', 'low fertility'),
    'metabolism': ('hungry', 'thrifty'),
    'sensory_gain': ('keen', 'dim'),
    'turn_gain': ('sharp turn', 'wide turn'),
    'spot': ('speckled', 'speckled'),
    'echo': ('echo', 'echo'),
    'drift': ('wobble', 'wobble'),
    'caution': ('hazard-shy', 'hazard-tolerant'),
    'generosity': ('gift-prone', 'gift-shy'),
    'aggression': ('attack-prone', 'attack-shy'),
}


def _positive_number(name, value, allow_zero=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite number')
    if allow_zero:
        if value < 0:
            raise ValueError(f'{name} must be nonnegative')
    elif value <= 0:
        raise ValueError(f'{name} must be positive')
    return float(value)


def derived_lifecycle(food_rate, aging_rate, repro_rate):
    food_rate = _positive_number('food_rate', food_rate)
    aging_rate = _positive_number('aging_rate', aging_rate)
    repro_rate = _positive_number('repro_rate', repro_rate, allow_zero=True)
    return {
        'seed_ticks': max(4, int(round(DEFAULTS['seed_ticks'] / food_rate))),
        'grow_ticks': max(8, int(round(DEFAULTS['grow_ticks'] / food_rate))),
        'cooldown_ticks': max(12, int(round(DEFAULTS['cooldown_ticks'] / food_rate))),
        'max_age': max(80, int(round(DEFAULTS['max_age'] / aging_rate))),
        'repro_enabled': repro_rate > 0,
        'repro_cooldown': 10 ** 9 if repro_rate <= 0 else max(12, int(round(DEFAULTS['repro_cooldown'] / repro_rate))),
        'min_repro_energy': 99.0 if repro_rate <= 0 else max(0.55, DEFAULTS['min_repro_energy'] - 0.15 * (repro_rate - 1.0)),
        'mate_radius': DEFAULTS['mate_radius'] if repro_rate <= 0 else DEFAULTS['mate_radius'] * (0.75 + 0.25 * repro_rate),
    }


def rules_from(overrides):
    rules = dict(DEFAULTS)
    explicit = {key: value for key, value in overrides.items() if key in rules and value is not None}
    rules.update(explicit)
    derived = derived_lifecycle(rules['food_rate'], rules['aging_rate'], rules['repro_rate'])
    for key, value in derived.items():
        if key not in explicit:
            rules[key] = value
    for key in INT_KEYS:
        if type(rules[key]) is not int or rules[key] < 0:
            raise ValueError(f'{key} must be a nonnegative integer')
        if rules[key] < 1 and key not in ('meal_life',):
            raise ValueError(f'{key} must be a positive integer')
    for key in RATE_KEYS:
        _positive_number(key, rules[key], allow_zero=(key in ('repro_rate', 'mutation_rate', 'mutation_sigma')))
    for key in ('seasons', 'scavenging', 'communication', 'social_learning', 'hazards', 'gifts', 'predation', 'lifetime_learning'):
        if type(rules[key]) is not bool:
            raise ValueError(f'{key} must be boolean')
    for key in ('scavenge_below', 'corpse_meal', 'compost_radius', 'compost_boost', 'signal_cost'):
        _positive_number(key, rules[key], allow_zero=True)
    for key in ('signal_range', 'sense_range', 'hazard_radius', 'hazard_drain', 'gift_amount', 'gift_range',
                'attack_range', 'attack_cost', 'attack_damage'):
        _positive_number(key, rules[key])
    _positive_number('gift_keep', rules['gift_keep'], allow_zero=False)
    _positive_number('attack_floor', rules['attack_floor'], allow_zero=True)
    if rules['gift_keep'] >= rules['gift_amount']:
        raise ValueError('gift_keep must be less than gift_amount')
    if rules['attack_range'] >= rules['sense_range']:
        raise ValueError('attack_range must be shorter than sense_range')
    for name in ('gift_chance', 'attack_chance'):
        chance = rules[name]
        if isinstance(chance, bool) or not isinstance(chance, (int, float)) or not 0 <= chance <= 1:
            raise ValueError(f'{name} must be between 0 and 1')
    if rules['agents'] > 50:
        raise ValueError('agents must be 50 or fewer on the CPU path')
    if rules['max_population'] > 60:
        raise ValueError('max_population must be 60 or fewer on the CPU path')
    frozen = rules['frozen_genes']
    if isinstance(frozen, str) or not isinstance(frozen, (list, tuple)):
        raise ValueError('frozen_genes must be a list of gene names')
    unknown = [gene for gene in frozen if gene not in GENE_BOUNDS]
    if unknown:
        raise ValueError('frozen_genes has unknown names: ' + ', '.join(unknown))
    rules['frozen_genes'] = list(frozen)
    if rules['agents'] > rules['max_population']:
        raise ValueError('agents cannot exceed max_population')
    if rules['map_half'] < 4:
        raise ValueError('map_half must be at least 4')
    if not rules.get('repro_enabled', True):
        rules['repro_enabled'] = False
    return rules


SEASONS = [('Bloom', 1.65), ('Abundance', 1.0), ('Drought', 0.3), ('Recovery', 0.8)]


def season_at(tick, rules):
    if not rules['seasons']:
        return {'name': 'Stable', 'index': -1, 'growth': 1.0, 'progress': 0.0,
                'remaining': 0, 'cycle': 0}
    length = rules['season_length']
    index = (tick // length) % len(SEASONS)
    name, growth = SEASONS[index]
    return {'name': name, 'index': index, 'growth': growth, 'progress': (tick % length) / length,
            'remaining': length - tick % length, 'cycle': tick // (length * len(SEASONS)) + 1}


def corpse_freshness(agent, tick, rules):
    until = agent.get('corpse_until')
    if agent['alive'] or until is None or tick >= until:
        return 0.0
    return max(0.0, min(1.0, (until - tick) / rules['corpse_ticks']))


def scavenge_corpses(agents, tick, rules, events):
    if not rules['scavenging']:
        return 0
    count = 0
    for corpse in sorted(agents, key=lambda a: a['id']):
        freshness = corpse_freshness(corpse, tick, rules)
        if not freshness or corpse.get('death_tick', tick) >= tick:
            continue
        eligible = [a for a in agents if a['alive'] and not a.get('ate', False)
                    and a['energy'] < rules['scavenge_below']
                    and math.hypot(a['x']-corpse['x'], a['y']-corpse['y']) < rules['eat_radius']]
        if not eligible:
            continue
        eater = min(eligible, key=lambda a: (math.hypot(a['x']-corpse['x'], a['y']-corpse['y']), a['id']))
        gained = min(rules['energy_max']-eater['energy'], rules['corpse_meal'] * freshness)
        if gained <= 0:
            continue
        eater['energy'] += gained
        eater['ate'] = True
        eater['scavenges'] = eater.get('scavenges', 0) + 1
        note_attack_meal(eater, corpse, tick, rules)
        corpse['corpse_until'] = None  # One finite meal; cannot also fertilize a patch.
        events.append({'tick': tick, 'kind': 'scavenged', 'agent': eater['id'], 'corpse': corpse['id'],
                       'energy': round(gained, 6), 'x': corpse['x'], 'y': corpse['y'],
                       'text': f'F{eater["id"]} scavenged F{corpse["id"]} (+{gained:.2f} energy)'})
        count += 1
    return count


def compost_corpse(corpse, patches, tick, rules, events):
    growing = [p for p in patches if p['stage'] in ('seed', 'growing') and
               math.hypot(p['x']-corpse['x'], p['y']-corpse['y']) <= rules['compost_radius']]
    if not growing or rules['compost_boost'] <= 0:
        return False
    patch = min(growing, key=lambda p: (math.hypot(p['x']-corpse['x'], p['y']-corpse['y']), p['id']))
    patch['timer'] = max(0.0, patch['timer'] - rules['compost_boost'])
    events.append({'tick': tick, 'kind': 'composted', 'agent': corpse['id'], 'patch': patch['id'],
                   'x': patch['x'], 'y': patch['y'],
                   'text': f'F{corpse["id"]} returned nutrients to patch {patch["id"]}'})
    return True


def spawn_agents(count, radius, energy):
    agents = []
    for index in range(count):
        angle = 2 * math.pi * index / count
        agents.append({
            'id': index,
            'x': radius * math.cos(angle),
            'y': radius * math.sin(angle),
            'heading': angle + math.pi,
            'energy': energy,
            'age': 0,
            'alive': True,
            'meals': 0,
            'ate': False,
            'birth_tick': 0,
            'death_tick': None,
            'cause_of_death': None,
            'corpse_until': None,
            'last_repro': -10 ** 6,
            'generation': 0,
            'parents': None,
            'offspring': 0,
            'genome': dict(BASE_GENOME),
            'mutations': {},
            'lineage': index,
            'contested': 0,
            'displaced': 0,
            'scavenges': 0,
        })
    return agents


def relocate_patch(patch, rng, rules):
    half = rules['map_half'] * 0.82
    patch['x'] = rng.uniform(-half, half)
    patch['y'] = rng.uniform(-half, half)


def spawn_patches(count, radius, rng, rules):
    patches = []
    for index in range(count):
        mature = index % 2 == 0
        patch = {
            'id': index,
            'x': 0.0,
            'y': 0.0,
            'stage': 'mature' if mature else 'growing',
            'timer': 0 if mature else rules['grow_ticks'] // 2,
            'nutrition': 1.0,
            'consumed_by': None,
        }
        relocate_patch(patch, rng, rules)
        patches.append(patch)
    return patches


def mature_locations(patches):
    return [(patch['x'], patch['y']) for patch in patches if patch['stage'] == 'mature']


def claim_patches(agents, patches, eat_radius):
    claimed = {}
    contests = []
    taken = set()
    for patch in patches:
        if patch['stage'] != 'mature':
            continue
        contenders = [agent for agent in agents
                      if agent['alive'] and agent['id'] not in taken
                      and math.hypot(agent['x'] - patch['x'], agent['y'] - patch['y']) < eat_radius]
        if not contenders:
            continue
        winner = min(contenders, key=lambda agent: agent['id'])
        claimed[patch['id']] = winner['id']
        taken.add(winner['id'])
        if len(contenders) > 1:
            losers = [agent['id'] for agent in contenders if agent['id'] != winner['id']]
            contests.append({'patch': patch['id'], 'winner': winner['id'], 'losers': losers})
            winner['contested'] = winner.get('contested', 0) + 1
            for agent in contenders:
                if agent['id'] != winner['id']:
                    agent['displaced'] = agent.get('displaced', 0) + 1
    return claimed, contests


def advance_patch(patch, rules, rng=None, growth=1.0):
    event = None
    if patch['stage'] == 'mature':
        return event
    patch['timer'] -= growth
    if patch['timer'] > 0:
        return event
    if patch['stage'] == 'cooldown':
        patch['stage'] = 'seed'
        patch['timer'] = rules['seed_ticks']
        patch['consumed_by'] = None
        if rng is not None:
            relocate_patch(patch, rng, rules)
    elif patch['stage'] == 'seed':
        patch['stage'] = 'growing'
        patch['timer'] = rules['grow_ticks']
    elif patch['stage'] == 'growing':
        patch['stage'] = 'mature'
        patch['timer'] = 0
        event = 'food_mature'
    return event


def kill(agent, tick, cause, corpse_ticks):
    agent['alive'] = False
    agent['energy'] = 0.0
    agent['death_tick'] = tick
    agent['cause_of_death'] = cause
    agent['corpse_until'] = tick + corpse_ticks


def round_genome(genome):
    return {gene: round(float(genome[gene]), 4) for gene in BASE_GENOME}


def inherit_genome(mother, father, rng, rules):
    child = {}
    mutations = {}
    rate = rules.get('mutation_rate', DEFAULTS['mutation_rate'])
    sigma = rules.get('mutation_sigma', DEFAULTS['mutation_sigma'])
    frozen = set(rules.get('frozen_genes') or ())
    for gene, (lo, hi) in GENE_BOUNDS.items():
        if gene in frozen:
            child[gene] = BASE_GENOME[gene]
            continue
        mid = 0.5 * (mother.get(gene, BASE_GENOME[gene]) + father.get(gene, BASE_GENOME[gene]))
        value = mid
        if rate > 0 and sigma > 0 and rng.random() < rate:
            if gene in ADDITIVE_GENES:
                value = max(lo, min(hi, mid + rng.gauss(0.0, sigma)))
            else:
                value = max(lo, min(hi, mid * (1.0 + rng.gauss(0.0, sigma))))
        child[gene] = value
        if abs(value - mid) > 1e-6:
            mutations[gene] = round(value - mid, 4)
    return child, mutations


def describe_mutations(mutations):
    names = []
    for gene, delta in mutations.items():
        labels = MUTATION_LABELS.get(gene)
        if not labels:
            names.append(gene)
            continue
        if gene == 'metabolism':
            names.append(labels[0] if delta > 0 else labels[1])
        else:
            names.append(labels[0] if delta >= 0 else labels[1])
    return names


def litter_size(genome):
    return 2 if genome.get('fertility', 1.0) >= 1.35 else 1


def lifespan_of(agent, rules):
    bonus = min(rules['meal_life_cap'], agent['meals'] * rules['meal_life'])
    return max(1, int(round(rules['max_age'] * agent['genome'].get('lifespan', 1.0) + bonus)))


PEDIGREE_DEPTH = 4


def family_tree(rows, focus, tick, max_depth=PEDIGREE_DEPTH):
    """Ancestors and descendants of one agent. Further kin are counted, not drawn."""
    if type(max_depth) is not int or max_depth < 0:
        raise ValueError('max_depth must be a nonnegative integer')
    present = []
    for row in rows:
        if row.get('birth_tick', 0) > tick:
            continue
        parents = row.get('parents')
        dead = row.get('death_tick') is not None and row.get('death_tick') <= tick
        present.append({
            'id': row['id'],
            'generation': row.get('generation', 0),
            'parents': list(parents) if parents else None,
            'alive': not dead,
            'cause': (row.get('cause') or row.get('cause_of_death')) if dead else None,
        })
    by_id = {row['id']: row for row in present}
    if focus not in by_id:
        return {'focus': focus, 'depth': max_depth, 'omitted': 0, 'nodes': []}
    children = {}
    for row in present:
        for parent in row['parents'] or []:
            children.setdefault(parent, []).append(row['id'])
    for parent in children:
        children[parent] = sorted(set(children[parent]))
    included = {focus: ('self', 0)}

    def add_layer(frontier, direction):
        nxt = []
        for agent_id, (relation, depth) in list(included.items()):
            if (agent_id in frontier) and depth < max_depth:
                linked = (by_id[agent_id]['parents'] or []) if direction == 'ancestor' else children.get(agent_id, [])
                for other in linked:
                    if other not in by_id or other in included:
                        continue
                    included[other] = (direction, depth + 1)
                    nxt.append(other)
        return nxt

    frontier = [focus]
    while frontier:
        frontier = add_layer(frontier, 'ancestor')
    frontier = [focus]
    while frontier:
        frontier = add_layer(frontier, 'descendant')
    omitted = set()

    def count_beyond(agent_id, direction):
        linked = (by_id[agent_id]['parents'] or []) if direction == 'ancestor' else children.get(agent_id, [])
        for other in linked:
            if other not in by_id or other in included or other in omitted:
                continue
            omitted.add(other)
            count_beyond(other, direction)

    for agent_id, (relation, depth) in included.items():
        if depth != max_depth:
            continue
        if relation in ('self', 'ancestor'):
            count_beyond(agent_id, 'ancestor')
        if relation in ('self', 'descendant'):
            count_beyond(agent_id, 'descendant')
    nodes = []
    for agent_id, (relation, depth) in included.items():
        row = by_id[agent_id]
        nodes.append({
            'id': agent_id, 'generation': row['generation'], 'alive': row['alive'],
            'cause': row['cause'], 'parents': row['parents'], 'relation': relation, 'depth': depth,
        })
    nodes.sort(key=lambda node: (
        0 if node['relation'] == 'ancestor' else 1 if node['relation'] == 'self' else 2,
        -node['depth'] if node['relation'] == 'ancestor' else node['depth'],
        node['id']))
    return {'focus': focus, 'depth': max_depth, 'omitted': len(omitted), 'nodes': nodes}


def roster_rows(agents):
    rows = []
    for agent in agents:
        parents = agent.get('parents')
        rows.append({
            'id': agent['id'],
            'generation': agent.get('generation', 0),
            'parents': list(parents) if parents else None,
            'birth_tick': agent.get('birth_tick', 0),
            'death_tick': agent.get('death_tick'),
            'cause': agent.get('cause_of_death'),
            'lineage': agent.get('lineage', agent['id']),
        })
    return rows


def lineage_table(agents):
    table = {}
    for agent in agents:
        lid = agent.get('lineage', agent['id'])
        row = table.setdefault(lid, {
            'founder': lid, 'born': 0, 'living': 0, 'max_gen': 0,
            'meals': 0, 'contested': 0, 'displaced': 0,
        })
        row['born'] += 1
        if agent['alive']:
            row['living'] += 1
        row['max_gen'] = max(row['max_gen'], agent['generation'])
        row['meals'] += agent['meals']
        row['contested'] += agent.get('contested', 0)
        row['displaced'] += agent.get('displaced', 0)
    return table


def living_by_generation(agents):
    counts = {}
    for agent in agents:
        if not agent['alive']:
            continue
        gen = agent['generation']
        counts[str(gen)] = counts.get(str(gen), 0) + 1
    return counts


def decoder_for(base, genome):
    return {
        'turn_sign': base['turn_sign'],
        'turn_gain': base['turn_gain'] * genome['turn_gain'],
        'turn_clip': base['turn_clip'],
        'speed_gain': base['speed_gain'] * genome['speed'],
        'sensory_sign': base['sensory_sign'],
    }


def genome_stats(agents):
    living = [agent for agent in agents if agent['alive']]
    empty = {gene: 0.0 for gene in BASE_GENOME}
    if not living:
        return empty, empty
    means = {}
    stds = {}
    count = len(living)
    for gene in BASE_GENOME:
        values = [agent['genome'][gene] for agent in living]
        mean = sum(values) / count
        variance = sum((value - mean) ** 2 for value in values) / count
        means[gene] = round(mean, 4)
        stds[gene] = round(variance ** 0.5, 4)
    return means, stds


def can_reproduce(agent, tick, rules):
    return (rules.get('repro_enabled', True)
            and agent['alive']
            and agent['age'] >= rules['min_repro_age']
            and agent['energy'] >= rules['min_repro_energy']
            and (tick - agent['last_repro']) >= rules['repro_cooldown'])


def reproduce(agents, circuits, graph, tick, rules, rng, events, disconnected, shuffle_seed):
    if not rules.get('repro_enabled', True):
        return 0
    candidates = [agent for agent in agents if can_reproduce(agent, tick, rules)]
    candidates.sort(key=lambda agent: agent['id'])
    used = set()
    births = 0
    for parent in candidates:
        if parent['id'] in used:
            continue
        partner = None
        best = rules['mate_radius']
        for other in candidates:
            if other['id'] <= parent['id'] or other['id'] in used:
                continue
            distance = math.hypot(parent['x'] - other['x'], parent['y'] - other['y'])
            if distance < best:
                best = distance
                partner = other
        if partner is None:
            continue
        if sum(agent['alive'] for agent in agents) >= rules['max_population']:
            events.append({'tick': tick, 'kind': 'repro_capped',
                           'text': f'population cap {rules["max_population"]} blocked a birth'})
            break
        used.add(parent['id'])
        used.add(partner['id'])
        parent['energy'] -= rules['repro_cost']
        partner['energy'] -= rules['repro_cost']
        parent['last_repro'] = tick
        partner['last_repro'] = tick
        parent['offspring'] += 1
        partner['offspring'] += 1
        first_genome, first_mutations = inherit_genome(parent['genome'], partner['genome'], rng, rules)
        extra = 1 if litter_size(first_genome) > 1 else 0
        for sibling in range(1 + extra):
            if sibling and sum(agent['alive'] for agent in agents) >= rules['max_population']:
                break
            genome, mutations = (first_genome, first_mutations) if sibling == 0 else inherit_genome(
                parent['genome'], partner['genome'], rng, rules)
            angle = rng.random() * 2 * math.pi
            half = rules['map_half']
            x = max(-half, min(half, (parent['x'] + partner['x']) / 2 + 0.35 * math.cos(angle)))
            y = max(-half, min(half, (parent['y'] + partner['y']) / 2 + 0.35 * math.sin(angle)))
            child_id = max(agent['id'] for agent in agents) + 1
            agents.append({
                'id': child_id,
                'x': x,
                'y': y,
                'heading': angle,
                'energy': rules['offspring_energy'],
                'age': 0,
                'alive': True,
                'meals': 0,
                'ate': False,
                'birth_tick': tick,
                'death_tick': None,
                'cause_of_death': None,
                'corpse_until': None,
                'last_repro': tick,
                'generation': max(parent['generation'], partner['generation']) + 1,
                'parents': (parent['id'], partner['id']),
                'offspring': 0,
                'genome': genome,
                'mutations': mutations,
                'lineage': parent['lineage'],
                'contested': 0,
                'displaced': 0,
            })
            circuits.append(Circuit(graph, disconnected=disconnected, shuffle_seed=shuffle_seed))
            labels = describe_mutations(mutations)
            mutated = ', '.join(labels) if labels else 'no mutation'
            events.append({
                'tick': tick,
                'kind': 'born',
                'agent': child_id,
                'parents': [parent['id'], partner['id']],
                'mutations': mutations,
                'labels': labels,
                'text': f'F{child_id} born to F{parent["id"]} and F{partner["id"]} · {mutated}',
            })
            births += 1
            if sibling:
                parent['offspring'] += 1
                partner['offspring'] += 1
    return births


def snapshot_agent(agent, left, right, speed):
    parents = agent['parents']
    return {
        'id': agent['id'],
        'x': round(agent['x'], 6),
        'y': round(agent['y'], 6),
        'heading': round(agent['heading'], 6),
        'energy': round(max(0.0, agent['energy']), 6),
        'age': agent['age'],
        'alive': agent['alive'],
        'meals': agent['meals'],
        'ate': agent['ate'],
        'cause_of_death': agent['cause_of_death'],
        'corpse': bool(agent['corpse_until'] is not None),
        'generation': agent['generation'],
        'parents': list(parents) if parents else None,
        'offspring': agent['offspring'],
        'genome': round_genome(agent['genome']),
        'mutations': dict(agent.get('mutations') or {}),
        'lineage': agent.get('lineage', agent['id']),
        'contested': agent.get('contested', 0),
        'displaced': agent.get('displaced', 0),
        'scavenges': agent.get('scavenges', 0),
        'intent': agent.get('intent', 'searching'),
        'target': copy.deepcopy(agent.get('target')),
        'memories': copy.deepcopy(agent.get('memories', [])),
        'social_history': copy.deepcopy(agent.get('social_history', [])),
        'social': dict(agent.get('social', {})),
        'left_motor': round(left, 6),
        'right_motor': round(right, 6),
        'speed': round(speed, 6),
    }


def snapshot_patch(patch):
    return {
        'id': patch['id'],
        'x': round(patch['x'], 6),
        'y': round(patch['y'], 6),
        'stage': patch['stage'],
    }


def spawn_hazards(rules, seed):
    """Fixed discs from the seed. Does not draw from the world random stream."""
    if not rules['hazards']:
        return []
    radius = rules['hazard_radius']
    span = max(0.0, rules['map_half'] - radius)
    discs = []
    for index in range(rules['hazard_count']):
        angle = (seed * 0.917 + index) * 2.399963
        ring = span * (0.45 + 0.5 * ((seed * 17 + index * 13) % 5) / 4)
        discs.append({
            'id': index,
            'x': round(max(-span, min(span, ring * math.cos(angle))), 6),
            'y': round(max(-span, min(span, ring * math.sin(angle))), 6),
            'radius': radius,
        })
    return discs


def nearest_hazard(agent, hazards, rules):
    best = None
    for disc in hazards:
        dist = math.hypot(agent['x'] - disc['x'], agent['y'] - disc['y'])
        if dist <= disc['radius'] or dist < rules['sense_range']:
            gap = dist - disc['radius']
            key = (gap, disc['id'])
            if best is None or key < best[0]:
                best = (key, disc, dist)
    return None if best is None else (best[1], best[2])


def avoidance_target(agent, disc):
    dx = agent['x'] - disc['x']
    dy = agent['y'] - disc['y']
    dist = math.hypot(dx, dy)
    if dist < 1e-9:
        dx, dy = math.cos(agent['heading'] + math.pi), math.sin(agent['heading'] + math.pi)
    else:
        dx, dy = dx / dist, dy / dist
    return {'x': agent['x'] + dx, 'y': agent['y'] + dy, 'kind': 'avoiding_hazard', 'id': disc['id']}


def gene_value(agent, name):
    return float((agent.get('genome') or {}).get(name, BASE_GENOME[name]))


# Same half-life and cap as sender scores. One row per action, not per partner.
ACTION_HALF_LIFE = 400
ACTION_EVIDENCE_CAP = 16
ATTACK_PENDING_CAP = 4


def init_action_learning(agent):
    agent.setdefault('action_learning', {
        'gift': {'useful': 0.0, 'empty': 0.0, 'seen_useful': 0, 'seen_empty': 0, 'last_tick': None},
        'attack': {'useful': 0.0, 'empty': 0.0, 'seen_useful': 0, 'seen_empty': 0, 'last_tick': None},
    })
    agent.setdefault('attack_pending', [])
    agent.setdefault('action_history', [])


def action_score(agent, action, tick, rules):
    """Neutral prior is one success and one failure. Learning off keeps that prior."""
    if action not in ('gift', 'attack'):
        raise ValueError('action must be gift or attack')
    if not rules.get('lifetime_learning', True):
        return 0.5
    init_action_learning(agent)
    row = agent['action_learning'][action]
    if row['last_tick'] is None:
        return 0.5
    decay = 2 ** (-max(0, tick - row['last_tick']) / ACTION_HALF_LIFE)
    useful, empty = row['useful'] * decay, row['empty'] * decay
    return (1 + useful) / (2 + useful + empty)


def learn_action(agent, action, tick, outcome, rules):
    if not rules.get('lifetime_learning', True) or outcome not in ('useful', 'empty'):
        return None
    init_action_learning(agent)
    row = agent['action_learning'][action]
    decay = 1.0 if row['last_tick'] is None else 2 ** (-max(0, tick - row['last_tick']) / ACTION_HALF_LIFE)
    row['useful'] *= decay
    row['empty'] *= decay
    row['useful' if outcome == 'useful' else 'empty'] += 1
    row['seen_useful' if outcome == 'useful' else 'seen_empty'] += 1
    total = row['useful'] + row['empty']
    if total > ACTION_EVIDENCE_CAP:
        scale = ACTION_EVIDENCE_CAP / total
        row['useful'] *= scale
        row['empty'] *= scale
    row['last_tick'] = tick
    score = action_score(agent, action, tick, rules)
    agent['action_history'] = (agent['action_history'] + [{
        'tick': tick, 'action': action, 'outcome': outcome, 'score': round(score, 6),
        'text': f'F{agent["id"]} {action} {outcome}',
    }])[-6:]
    return score


def action_view(agent, tick, rules):
    rows = []
    for action in ('gift', 'attack'):
        table = ((agent.get('action_learning') or {}).get(action) or {})
        score = action_score(agent, action, tick, rules)
        if not rules.get('lifetime_learning', True) or table.get('last_tick') is None:
            useful = empty = 0.0
        else:
            decay = 2 ** (-max(0, tick - table['last_tick']) / ACTION_HALF_LIFE)
            useful, empty = table['useful'] * decay, table['empty'] * decay
        rows.append({
            'action': action, 'score': round(score, 6),
            'useful': round(useful, 4), 'empty': round(empty, 4),
            'seen_useful': table.get('seen_useful', 0), 'seen_empty': table.get('seen_empty', 0),
        })
    return rows


def action_totals(agents):
    totals = {'gift_useful': 0, 'gift_empty': 0, 'attack_useful': 0, 'attack_empty': 0}
    for agent in agents:
        table = agent.get('action_learning') or {}
        for action in ('gift', 'attack'):
            row = table.get(action) or {}
            totals[action + '_useful'] += row.get('seen_useful', 0)
            totals[action + '_empty'] += row.get('seen_empty', 0)
    return totals


def note_attack_meal(eater, corpse, tick, rules):
    """The attacker ate this corpse. That is local evidence, not a hidden reward."""
    pending = eater.get('attack_pending') or []
    match = next((row for row in pending if row['target'] == corpse['id']), None)
    if match is None:
        return
    pending.remove(match)
    learn_action(eater, 'attack', tick, 'useful', rules)


def settle_attack_learning(agents, tick, rules):
    """Arrival at a gone corpse counts. A corpse never reached does not."""
    if not rules.get('lifetime_learning', True):
        return
    by_id = {agent['id']: agent for agent in agents}
    for agent in agents:
        pending = agent.get('attack_pending') or []
        if not pending:
            continue
        kept = []
        for row in pending:
            corpse = by_id.get(row['target'])
            fresh = corpse is not None and corpse_freshness(corpse, tick, rules) > 0
            arrived = agent['alive'] and math.hypot(agent['x'] - row['x'], agent['y'] - row['y']) < rules['eat_radius']
            if arrived and not fresh:
                learn_action(agent, 'attack', tick, 'empty', rules)
                continue
            if not agent['alive'] or tick >= row['until']:
                continue
            kept.append(row)
        agent['attack_pending'] = kept


def remember_attack(attacker, target, tick, rules):
    if not rules.get('lifetime_learning', True):
        return
    init_action_learning(attacker)
    pending = attacker['attack_pending']
    if len(pending) >= ATTACK_PENDING_CAP:
        pending.pop(0)
    pending.append({
        'target': target['id'], 'x': target['x'], 'y': target['y'],
        'until': tick + rules['corpse_ticks'],
    })


def compete_hazard(agent, choice, hazards, rules):
    sensed = nearest_hazard(agent, hazards, rules) if rules['hazards'] else None
    if sensed is None:
        return choice
    disc, dist = sensed
    gap = dist - disc['radius']
    food = math.inf if choice is None else math.hypot(choice['x'] - agent['x'], choice['y'] - agent['y'])
    caution = gene_value(agent, 'caution')
    if gap <= 0 or gap < food * caution:
        return avoidance_target(agent, disc)
    return choice


def init_gifts(agent):
    agent.setdefault('last_gift', -10 ** 9)
    agent.setdefault('gifts_sent', 0)
    agent.setdefault('gifts_received', 0)
    agent.setdefault('gift_paid', 0.0)
    agent.setdefault('gift_gained', 0.0)
    agent.setdefault('gift_alive_later', 0)
    agent.setdefault('gift_checks', 0)
    agent.setdefault('gift_pending', [])


def gift_willing(agent, tick, rules):
    roll = ((agent['id'] + 1) * 137 + tick * 53 + 91) % 1009 / 1009
    scale = gene_value(agent, 'generosity') * 2.0 * action_score(agent, 'gift', tick, rules)
    return roll < min(1.0, rules['gift_chance'] * scale)


def exchange_gifts(agents, tick, rules, events):
    """Directed gift. The recipient gains less than the donor pays. Not friendship."""
    for agent in agents:
        init_gifts(agent)
        pending = []
        for row in agent['gift_pending']:
            if tick < row['check']:
                pending.append(row)
                continue
            recipient = next((other for other in agents if other['id'] == row['recipient']), None)
            agent['gift_checks'] += 1
            if recipient is not None and recipient['alive']:
                agent['gift_alive_later'] += 1
            if agent['alive'] and 'energy' in row:
                outcome = 'useful' if agent['energy'] >= row['energy'] - 1e-9 else 'empty'
                learn_action(agent, 'gift', tick, outcome, rules)
        agent['gift_pending'] = pending
    if not rules['gifts']:
        return 0
    sent = 0
    for donor in sorted((agent for agent in agents if agent['alive']), key=lambda agent: agent['id']):
        if tick - donor['last_gift'] < rules['gift_cooldown']:
            continue
        if donor['energy'] < rules['gift_amount'] + 0.2:
            continue
        neighbours = [other for other in agents if other['alive'] and other['id'] != donor['id']
                      and math.hypot(donor['x'] - other['x'], donor['y'] - other['y']) <= rules['gift_range']]
        if not neighbours:
            continue
        donor['last_gift'] = tick
        if not gift_willing(donor, tick, rules):
            continue
        recipient = min(neighbours, key=lambda other: (
            math.hypot(donor['x'] - other['x'], donor['y'] - other['y']), other['id']))
        gain = min(rules['energy_max'] - recipient['energy'], rules['gift_keep'])
        gain = max(0.0, gain)
        donor['energy'] -= rules['gift_amount']
        recipient['energy'] += gain
        donor['gifts_sent'] += 1
        donor['gift_paid'] += rules['gift_amount']
        recipient['gifts_received'] += 1
        recipient['gift_gained'] += gain
        donor['gift_pending'].append({
            'tick': tick, 'recipient': recipient['id'], 'check': tick + rules['gift_follow'],
            'energy': donor['energy'],
        })
        sent += 1
        events.append({'tick': tick, 'kind': 'gift', 'agent': donor['id'], 'recipient': recipient['id'],
                       'paid': rules['gift_amount'], 'gained': round(gain, 6),
                       'text': f'F{donor["id"]} gave energy to F{recipient["id"]} ({rules["gift_amount"]:.2f} paid, {gain:.2f} received)'})
    return sent


def gift_totals(agents):
    for agent in agents:
        init_gifts(agent)
    return {
        'sent': sum(agent['gifts_sent'] for agent in agents),
        'received': sum(agent['gifts_received'] for agent in agents),
        'energy_paid': round(sum(agent['gift_paid'] for agent in agents), 6),
        'energy_gained': round(sum(agent['gift_gained'] for agent in agents), 6),
        'alive_later': sum(agent['gift_alive_later'] for agent in agents),
        'checked': sum(agent['gift_checks'] for agent in agents),
    }


def init_attacks(agent):
    agent.setdefault('last_attack', -10 ** 9)
    agent.setdefault('attacks', 0)


def attack_willing(agent, tick, rules):
    roll = ((agent['id'] + 1) * 149 + tick * 59 + 113) % 1009 / 1009
    scale = gene_value(agent, 'aggression') * 2.0 * action_score(agent, 'attack', tick, rules)
    return roll < min(1.0, rules['attack_chance'] * scale)


def resolve_predation(agents, patches, tick, rules, events):
    """Costly attack. A kill leaves a corpse; it does not hand the attacker a meal."""
    for agent in agents:
        init_attacks(agent)
    if not rules['predation']:
        return 0
    kills = 0
    for attacker in sorted((agent for agent in agents if agent['alive']), key=lambda agent: agent['id']):
        if tick - attacker['last_attack'] < rules['attack_cooldown']:
            continue
        if attacker['energy'] <= rules['attack_floor']:
            continue
        neighbours = [other for other in agents if other['alive'] and other['id'] != attacker['id']
                      and math.hypot(attacker['x'] - other['x'], attacker['y'] - other['y']) <= rules['attack_range']]
        if not neighbours:
            continue
        target = min(neighbours, key=lambda other: (
            math.hypot(attacker['x'] - other['x'], attacker['y'] - other['y']), other['id']))
        gap = math.hypot(attacker['x'] - target['x'], attacker['y'] - target['y'])
        food = min((math.hypot(attacker['x'] - patch['x'], attacker['y'] - patch['y'])
                    for patch in patches if patch['stage'] == 'mature'), default=math.inf)
        if gap >= food:
            continue
        attacker['last_attack'] = tick
        if not attack_willing(attacker, tick, rules):
            continue
        if not target['alive']:
            continue
        attacker['energy'] -= rules['attack_cost']
        attacker['attacks'] += 1
        target['energy'] -= rules['attack_damage']
        killed = target['energy'] <= 0
        if killed:
            kill(target, tick, 'predation', rules['corpse_ticks'])
            remember_attack(attacker, target, tick, rules)
            kills += 1
        events.append({
            'tick': tick, 'kind': 'attack', 'agent': attacker['id'], 'target': target['id'], 'killed': killed,
            'text': f'F{attacker["id"]} attacked F{target["id"]}' + (' and killed them' if killed else ''),
        })
    return kills


def resolve_death(agent, rules, in_hazard, predation=False):
    """First match: predation, hazard, starvation, old age. One energy pool."""
    if predation:
        return 'predation'
    if in_hazard and agent['energy'] <= 0:
        return 'hazard'
    if agent['energy'] <= 0:
        return 'starvation'
    if agent['age'] >= lifespan_of(agent, rules):
        return 'old_age'
    return None


def motors_for(agents, circuits, edible, decoder, rules, drive_enabled, tick=0, events=None, hazards=None):
    motors = []
    for agent, circuit in zip(agents, circuits):
        agent['ate'] = False
        speed = 0.0
        if not agent['alive']:
            motors.append((0.0, 0.0, speed))
            continue
        agent['age'] += 1
        options = [{'x': x, 'y': y, 'kind': 'foraging'} for x, y in edible]
        if rules['scavenging'] and agent['energy'] < rules['scavenge_below']:
            options += [{'x': a['x'], 'y': a['y'], 'kind': 'scavenging', 'id': a['id']}
                        for a in agents if corpse_freshness(a, tick, rules) > 0]
        choice = social.select_target(agent, options, tick, rules, events if events is not None else []) if drive_enabled else None
        choice = compete_hazard(agent, choice, hazards or [], rules) if drive_enabled else choice
        distance = math.hypot(choice['x']-agent['x'], choice['y']-agent['y']) if choice else math.inf
        target = (choice['x'], choice['y']) if choice else None
        agent['intent'] = choice['kind'] if choice and drive_enabled else 'searching'
        agent['target'] = choice if agent['intent'] != 'searching' else None
        bearing = 0.0
        stimulus = 0.0
        if target is not None and drive_enabled:
            bearing = math.atan2(target[1] - agent['y'], target[0] - agent['x']) - agent['heading']
            bearing = math.atan2(math.sin(bearing), math.cos(bearing))
            stimulus = (0.5 if choice['kind'] == 'following_signal' else max(0.0, 1.0 - distance / rules['sense_range'])) * agent['genome']['sensory_gain']
        body = decoder_for(decoder, agent['genome'])
        circuit.step(sensory_drives(circuit.nodes, body, bearing, stimulus))
        left, right = circuit.motors()
        agent['x'], agent['y'], agent['heading'], speed = integrate_motion(
            body, agent['x'], agent['y'], agent['heading'], left, right)
        # Reflect off the finite map boundary; no hidden teleportation across the map.
        half = rules['map_half']
        if abs(agent['x']) > half:
            agent['x'] = max(-half, min(half, agent['x']))
            agent['heading'] = math.pi - agent['heading']
        if abs(agent['y']) > half:
            agent['y'] = max(-half, min(half, agent['y']))
            agent['heading'] = -agent['heading']
        agent['heading'] += 0.01 * agent['genome'].get('drift', 0.0) * math.sin(agent['age'] * 0.19)
        motors.append((left, right, speed))
    return motors


def simulate_ecosystem(path, ticks, seed, *, drive_enabled=True, disconnected=False, shuffle_seed=None,
                       turn_sign=1, turn_gain=0.15, turn_clip=0.3, speed_gain=0.13, sensory_sign=1, **overrides):
    if type(ticks) is not int or ticks < 1:
        raise ValueError('ticks must be a positive integer')
    rules = rules_from(overrides)
    decoder = validate_decoder(turn_sign, turn_gain, turn_clip, speed_gain, sensory_sign)
    graph = json.loads(Path(path).read_text())
    validate_graph(graph)
    rng = random.Random(seed)
    agents = spawn_agents(rules['agents'], rules['map_half'] * 0.85, rules['energy_start'])
    patches = spawn_patches(rules['patches'], rules['map_half'] * 0.4, rng, rules)
    hazards = spawn_hazards(rules, seed)
    hazard_deaths = 0
    hazard_entries = 0
    circuits = [Circuit(graph, disconnected=disconnected, shuffle_seed=shuffle_seed) for _ in agents]
    events = []
    history = []
    signals = []
    births = 0
    peak = rules['agents']
    contested_meals = 0
    displaced = 0
    scavenged = composted = 0
    for tick in range(ticks):
        environment = season_at(tick, rules)
        if rules['seasons'] and tick % rules['season_length'] == 0:
            events.append({'tick': tick, 'kind': 'season', 'text': f'{environment["name"]}: plant growth ×{environment["growth"]:.2f}'})
        social.begin_tick(agents, patches, signals, tick, rules, events)
        motors = motors_for(agents, circuits, mature_locations(patches), decoder, rules, drive_enabled, tick, events, hazards)
        claimed, contests = claim_patches(agents, patches, rules['eat_radius'])
        contested_meals += len(contests)
        displaced += sum(len(row['losers']) for row in contests)
        for row in contests:
            events.append({'tick': tick, 'kind': 'contested', 'patch': row['patch'],
                           'winner': row['winner'], 'losers': row['losers'],
                           'text': f'F{row["winner"]} beat {len(row["losers"])} rival(s) to patch {row["patch"]}'})
        for patch in patches:
            if patch['id'] in claimed:
                eater = next(agent for agent in agents if agent['id'] == claimed[patch['id']])
                eater['meal_position'] = {'x': patch['x'], 'y': patch['y']}
                eater['ate'] = True
                eater['meals'] += 1
                eater['energy'] = min(rules['energy_max'], eater['energy'] + rules['meal'] * patch['nutrition'])
                patch['stage'] = 'cooldown'
                patch['timer'] = rules['cooldown_ticks']
                patch['consumed_by'] = eater['id']
                events.append({'tick': tick, 'kind': 'ate', 'agent': eater['id'], 'patch': patch['id'],
                               'text': f'F{eater["id"]} ate patch {patch["id"]}'})
            else:
                matured = advance_patch(patch, rules, rng, environment['growth'])
                if matured:
                    events.append({'tick': tick, 'kind': 'food_mature', 'patch': patch['id'],
                                   'text': f'patch {patch["id"]} matured at ({patch["x"]:.1f},{patch["y"]:.1f})'})
        social.end_tick(agents, tick, rules, events)
        exchange_gifts(agents, tick, rules, events)
        resolve_predation(agents, patches, tick, rules, events)
        scavenged += scavenge_corpses(agents, tick, rules, events)
        births += reproduce(agents, circuits, graph, tick, rules, rng, events, disconnected, shuffle_seed)
        while len(motors) < len(agents):
            motors.append((0.0, 0.0, 0.0))
        for agent, (left, right, speed) in zip(agents, motors):
            if not agent['alive']:
                continue
            agent['energy'] -= rules['base_drain'] * agent['genome']['metabolism'] + rules['move_cost'] * speed
            inside = nearest_hazard(agent, hazards, rules)
            in_hazard = inside is not None and inside[1] <= inside[0]['radius']
            if in_hazard and not agent.get('inside_hazard'):
                hazard_entries += 1
            agent['inside_hazard'] = in_hazard
            if in_hazard:
                agent['energy'] -= rules['hazard_drain']
            cause = resolve_death(agent, rules, in_hazard)
            if cause == 'hazard':
                hazard_deaths += 1
            if cause:
                kill(agent, tick, cause, rules['corpse_ticks'])
                label = {'hazard': 'died in a hazard', 'starvation': 'starved', 'old_age': 'died of old age',
                         'predation': 'was killed'}[cause]
                events.append({'tick': tick, 'kind': 'died', 'agent': agent['id'], 'cause': cause,
                               'text': f'F{agent["id"]} {label}'})
        corpses = []
        for agent in agents:
            if agent['corpse_until'] is None:
                continue
            if tick >= agent['corpse_until']:
                composted += int(compost_corpse(agent, patches, tick, rules, events))
                events.append({'tick': tick, 'kind': 'corpse_decayed', 'agent': agent['id'],
                               'text': f'F{agent["id"]} corpse decayed'})
                agent['corpse_until'] = None
            else:
                corpses.append({'id': agent['id'], 'x': round(agent['x'], 6), 'y': round(agent['y'], 6),
                                'cause': agent['cause_of_death'], 'freshness': round(corpse_freshness(agent, tick, rules), 6)})
        settle_attack_learning(agents, tick, rules)
        alive = [agent for agent in agents if agent['alive']]
        peak = max(peak, len(alive))
        means, stds = genome_stats(agents)
        record = (tick % rules['record_every'] == 0) or (tick == ticks - 1)
        if record:
            motor_by_id = {agent['id']: motor for agent, motor in zip(agents, motors)}
            visible = [agent for agent in agents if agent['alive'] or agent['corpse_until'] is not None]
            frames = []
            for agent in visible:
                row = snapshot_agent(agent, *motor_by_id.get(agent['id'], (0.0, 0.0, 0.0)))
                row['life_span'] = lifespan_of(agent, rules)
                row['relationships'] = social.relationship_view(agent, tick)
                row['action_scores'] = action_view(agent, tick, rules)
                row['action_history'] = copy.deepcopy(agent.get('action_history') or [])
                frames.append(row)
            history.append({
                'tick': tick,
                'agents': frames,
                'patches': [snapshot_patch(patch) for patch in patches],
                'corpses': corpses,
                'alive': len(alive),
                'born': births,
                'mature_food': sum(patch['stage'] == 'mature' for patch in patches),
                'mean_energy': round(sum(agent['energy'] for agent in alive) / len(alive), 6) if alive else 0.0,
                'mean_speed': means['speed'],
                'mean_metabolism': means['metabolism'],
                'mean_lifespan': means['lifespan'],
                'mean_fertility': means['fertility'],
                'genome_mean': means,
                'genome_std': stds,
                'living_by_gen': living_by_generation(agents),
                'contested': contested_meals,
                'displaced': displaced,
                'signals': copy.deepcopy(signals), 'social': social.totals(agents),
                'environment': environment, 'scavenged': scavenged, 'composted': composted,
                'hazards': [dict(disc) for disc in hazards], 'hazard_deaths': hazard_deaths,
                'hazard_entries': hazard_entries,
                'predation': sum(agent['cause_of_death'] == 'predation' for agent in agents),
                'gifts': gift_totals(agents),
            })
    return {
        'mode': 'ecosystem',
        'rules': rules,
        'events': events,
        'final': {
            'alive': sum(agent['alive'] for agent in agents),
            'starved': sum(agent['cause_of_death'] == 'starvation' for agent in agents),
            'old_age': sum(agent['cause_of_death'] == 'old_age' for agent in agents),
            'meals': sum(agent['meals'] for agent in agents),
            'births': births,
            'peak': peak,
            'generation': max((agent['generation'] for agent in agents), default=0),
            'genome_mean': genome_stats(agents)[0],
            'genome_std': genome_stats(agents)[1],
            'contested': contested_meals,
            'displaced': displaced,
            'social': social.totals(agents),
            'scavenged': scavenged, 'composted': composted,
            'hazard': hazard_deaths,
            'hazard_entries': hazard_entries,
            'predation': sum(agent['cause_of_death'] == 'predation' for agent in agents),
            'attacks': sum(agent.get('attacks', 0) for agent in agents),
            'personality_mean': {
                gene: round(sum(agent['genome'][gene] for agent in agents) / len(agents), 4)
                for gene in ('caution', 'generosity', 'aggression')
            },
            'gifts': gift_totals(agents),
            'actions': action_totals(agents),
            'lineages': lineage_table(agents),
            'living_by_gen': living_by_generation(agents),
        },
        'roster': roster_rows(agents),
        'hazards': hazards,
        'ticks': history,
    }


def summarize_ecosystem(result):
    final = result['final']
    rules = result['rules']
    last = result['ticks'][-1]
    means = final.get('genome_mean') or {}
    return (f"ecosystem {rules['agents']} start, {rules['patches']} patches, {last['tick'] + 1} ticks; "
            f"alive {final['alive']}, births {final['births']}, gen {final['generation']}, "
            f"starved {final['starved']}, old_age {final['old_age']}, "
            f"meals {final['meals']}, contested {final.get('contested', 0)}, "
            f"mature food {last['mature_food']}, "
            f"mean speed {means.get('speed', 1):.2f}, life {means.get('lifespan', 1):.2f}, "
            f"fertility {means.get('fertility', 1):.2f}")
