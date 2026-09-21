"""Engineered local food messages and bounded location memory, not fly cognition."""
import math

DEFAULTS = dict(communication=True, signal_range=18.0, signal_ticks=24,
                signal_cooldown=60, signal_cost=0.01, memory_ticks=180)


def initialize(agent):
    agent.setdefault('memories', [])
    agent.setdefault('social_history', [])
    agent.setdefault('last_signal', -10**9)
    agent.setdefault('social', dict(sent=0, received=0, followed=0, meals=0, empty=0, expired=0))


def distance(a, b):
    return math.hypot(a['x'] - b['x'], a['y'] - b['y'])


def willing(agent, tick, gene):
    # Separate deterministic decision stream; messaging does not consume world RNG.
    salt = 37 if gene == 'signalling' else 71
    roll = ((agent['id'] + 1) * 137 + tick * 53 + salt) % 1009 / 1009
    return roll < agent['genome'].get(gene, 0.5)


def remember_event(agent, tick, outcome, memory, events):
    row = dict(tick=tick, kind='signal_' + outcome, agent=agent['id'], source=memory['source'],
               x=memory['x'], y=memory['y'],
               text=f'F{agent["id"]}: {outcome} after food signal from F{memory["source"]}')
    agent['social_history'] = (agent['social_history'] + [dict(row)])[-6:]
    events.append(row)


def begin_tick(agents, patches, signals, tick, rules, events):
    signals[:] = [s for s in signals if s['until'] > tick]
    for a in agents:
        initialize(a)
        a['meal_position'] = None
        if not rules['communication'] or not a['alive']:
            a['memories'] = []
            continue
        for m in a['memories']:
            if m['until'] <= tick and m['followed']:
                a['social']['expired'] += 1
                remember_event(a, tick, 'expired', m, events)
        a['memories'] = [m for m in a['memories'] if m['until'] > tick]
    if not rules['communication']:
        signals.clear()
        return
    fresh = []
    for a in sorted(agents, key=lambda a: a['id']):
        if not a['alive'] or tick - a['last_signal'] < rules['signal_cooldown']:
            continue
        visible = [p for p in patches if p['stage'] == 'mature' and distance(a, p) < rules['sense_range']]
        if not visible or a['energy'] < rules['signal_cost'] + 0.2:
            continue
        a['last_signal'] = tick  # Cooldown also bounds unsuccessful emission decisions.
        if not willing(a, tick, 'signalling'):
            continue
        p = min(visible, key=lambda p: (distance(a, p), p['id']))
        a['energy'] -= rules['signal_cost']
        a['social']['sent'] += 1
        s = dict(id=f'{tick}:{a["id"]}', source=a['id'], x=p['x'], y=p['y'],
                 origin_x=a['x'], origin_y=a['y'], patch=p['id'], tick=tick,
                 until=tick + rules['signal_ticks'])
        fresh.append(s)
        events.append(dict(tick=tick, kind='signal_sent', agent=a['id'], x=a['x'], y=a['y'],
                           text=f'F{a["id"]} signalled food at patch {p["id"]}'))
    signals.extend(fresh)
    for a in agents:
        if not a['alive']:
            continue
        for s in fresh:
            if a['id'] == s['source'] or math.hypot(a['x']-s['origin_x'], a['y']-s['origin_y']) > rules['signal_range']:
                continue
            a['social']['received'] += 1
            if not willing(a, tick + s['source'], 'responsiveness'):
                continue
            # Store the reported location without reading its current hidden world state.
            existing = next((m for m in a['memories'] if m['source'] == s['source'] and
                             m['x'] == s['x'] and m['y'] == s['y']), None)
            if existing:
                continue
            if len(a['memories']) >= 4:
                # Keep in-progress trips instead of silently losing their outcomes.
                removable = next((m for m in a['memories'] if not m['followed']), None)
                if removable is None:
                    continue
                a['memories'].remove(removable)
            a['memories'].append(dict(s, until=tick + rules['memory_ticks'], followed=False))


def select_target(agent, direct, tick, rules, events):
    options = [p for p in direct if distance(agent, p) < rules['sense_range']]
    if rules['communication']:
        options = [dict(m, kind='following_signal') for m in agent.get('memories', [])] + options
    choice = min(options, key=lambda p: distance(agent, p), default=None)
    if choice and choice['kind'] == 'following_signal':
        memory = next(m for m in agent['memories'] if m['id'] == choice['id'])
        if not memory['followed']:
            memory['followed'] = True
            agent['social']['followed'] += 1
            remember_event(agent, tick, 'followed', memory, events)
    return choice


def end_tick(agents, tick, rules, events):
    for a in agents:
        target = a.get('target')
        if not a['alive'] or not target or target['kind'] != 'following_signal':
            continue
        memory = next((m for m in a['memories'] if m['id'] == target['id']), None)
        if memory is None or distance(a, memory) >= rules['eat_radius']:
            continue
        meal = a.get('meal_position')
        outcome = 'meals' if meal and distance(meal, memory) < 1e-6 else 'empty'
        a['social'][outcome] += 1
        remember_event(a, tick, outcome, memory, events)
        a['memories'].remove(memory)


def totals(agents):
    return {key: sum(a.get('social', {}).get(key, 0) for a in agents)
            for key in ('sent', 'received', 'followed', 'meals', 'empty', 'expired')}
