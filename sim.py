"""Small connectome-driven foraging experiment; dynamics are exploratory."""
import argparse
import csv
import json
import math
import random
from pathlib import Path


def validate_graph(graph):
    if not isinstance(graph, dict) or not isinstance(graph.get('nodes'), list) or not isinstance(graph.get('edges'), list):
        raise ValueError('Graph must contain nodes and edges lists')
    if not graph['nodes']:
        raise ValueError('Graph cannot be empty')
    ids = set()
    for n in graph['nodes']:
        if not isinstance(n, dict) or not isinstance(n.get('id'), (str, int)) or isinstance(n['id'], bool):
            raise ValueError('Each neuron needs a string or integer ID')
        key = str(n['id'])
        if not key or key in ids:
            raise ValueError('Neuron IDs must be non-empty and unique')
        ids.add(key)
        if n.get('role') not in ['sensory', 'interneuron', 'motor']:
            raise ValueError(f'Unknown simulator role for neuron {key}')
        if n.get('side') not in ['left', 'right', 'center']:
            raise ValueError(f'Unknown side for neuron {key}')
    pairs = set()
    for e in graph['edges']:
        if not isinstance(e, dict) or str(e.get('pre')) not in ids or str(e.get('post')) not in ids:
            raise ValueError('Connection references an unknown neuron')
        pair = str(e['pre']), str(e['post'])
        if pair in pairs:
            raise ValueError('Duplicate connections must be aggregated before simulation')
        pairs.add(pair)
        w = e.get('weight')
        if isinstance(w, bool) or not isinstance(w, (int, float)) or not math.isfinite(w) or w <= 0:
            raise ValueError('Connection weights must be finite and positive')
    if not any(n['role'] == 'sensory' for n in graph['nodes']):
        raise ValueError('Graph needs sensory interface nodes')
    for side in ['left', 'right']:
        if not any(n['role'] == 'motor' and n['side'] == side for n in graph['nodes']):
            raise ValueError('Graph needs left and right motor interface nodes')
    return graph


class Circuit:
    """All-excitatory rate controller; NOT a physiological spiking model."""
    def __init__(self, graph, disconnected=False, shuffle_seed=None):
        validate_graph(graph)
        self.nodes = graph['nodes']
        ids = {str(n['id']): i for i, n in enumerate(self.nodes)}
        self.incoming = [[] for _ in self.nodes]
        edges = graph['edges']
        # Control: shuffle sources across edges, preserving the target weight totals.
        # It may introduce self/parallel connections; this is a null model, not data.
        sources = [e['pre'] for e in edges]
        if shuffle_seed is not None:
            random.Random(shuffle_seed).shuffle(sources)
        if not disconnected:
            for source, e in zip(sources, edges):
                self.incoming[ids[str(e['post'])]].append((ids[str(source)], e['weight'] / 100.0))
        self.activity = [0.0] * len(self.nodes)

    def step(self, drives):
        if len(drives) != len(self.nodes) or any(not math.isfinite(d) or d < 0 for d in drives):
            raise ValueError('Drives must be one finite nonnegative value per neuron')
        old = self.activity
        self.activity = [max(0.0, min(1.0, .75 * old[i] + .25 * (drives[i] + sum(old[j] * w for j, w in incoming))))
                         for i, incoming in enumerate(self.incoming)]
        return self.activity

    def motors(self):
        return tuple(sum(a for a, n in zip(self.activity, self.nodes) if n['role'] == 'motor' and n['side'] == side)
                     for side in ['left', 'right'])


def sensory_drives(nodes, decoder, bearing, stimulus):
    drives = [0.0] * len(nodes)
    lateral = math.sin(bearing)
    for i, node in enumerate(nodes):
        if node['role'] != 'sensory':
            continue
        side = node['side']
        if side == 'left':
            laterality = decoder['sensory_sign'] * lateral
        elif side == 'right':
            laterality = -decoder['sensory_sign'] * lateral
        else:
            laterality = 0.0
        drives[i] = stimulus * (1 + laterality)
    return drives


def integrate_motion(decoder, x, y, heading, left, right):
    heading += max(-decoder['turn_clip'], min(decoder['turn_clip'],
                                             (right - left) * decoder['turn_sign'] * decoder['turn_gain']))
    speed = decoder['speed_gain'] * min(1, left + right)
    x += speed * math.cos(heading)
    y += speed * math.sin(heading)
    return x, y, heading, speed


def nearest_point(x, y, points):
    if not points:
        return None, float('inf')
    best = min(points, key=lambda point: math.hypot(point[0] - x, point[1] - y))
    return best, math.hypot(best[0] - x, best[1] - y)


def validate_decoder(turn_sign=1, turn_gain=0.15, turn_clip=0.3, speed_gain=0.13, sensory_sign=1):
    if isinstance(turn_sign, bool) or turn_sign not in (1, -1):
        raise ValueError('turn_sign must be 1 or -1')
    if isinstance(sensory_sign, bool) or sensory_sign not in (1, -1):
        raise ValueError('sensory_sign must be 1 or -1')
    for name, value in [('turn_gain', turn_gain), ('turn_clip', turn_clip), ('speed_gain', speed_gain)]:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f'{name} must be finite and positive')
    return {'turn_sign': int(turn_sign), 'turn_gain': float(turn_gain), 'turn_clip': float(turn_clip),
            'speed_gain': float(speed_gain), 'sensory_sign': int(sensory_sign)}


def simulate(path, ticks, seed, *, drive_enabled=True, disconnected=False,
             shuffle_seed=None, initial_food=(5.0, 3.0), turn_sign=1, turn_gain=0.15,
             turn_clip=0.3, speed_gain=0.13, sensory_sign=1):
    if type(ticks) is not int or ticks < 1:
        raise ValueError('ticks must be a positive integer')
    decoder = validate_decoder(turn_sign, turn_gain, turn_clip, speed_gain, sensory_sign)
    graph = json.loads(Path(path).read_text())
    circuit = Circuit(graph, disconnected=disconnected, shuffle_seed=shuffle_seed)
    rng = random.Random(seed)
    x = y = heading = 0.0
    food = initial_food
    if len(food) != 2 or not all(math.isfinite(v) for v in food):
        raise ValueError('initial_food must be two finite coordinates')
    history = []
    for tick in range(ticks):
        bearing = math.atan2(food[1] - y, food[0] - x) - heading
        bearing = math.atan2(math.sin(bearing), math.cos(bearing))
        distance = math.hypot(food[0] - x, food[1] - y)
        stimulus = max(0.0, 1.0 - distance / 12.0) if drive_enabled else 0.0
        drives = sensory_drives(circuit.nodes, decoder, bearing, stimulus)
        activity = circuit.step(drives)
        left, right = circuit.motors()
        x, y, heading, _speed = integrate_motion(decoder, x, y, heading, left, right)
        ate = math.hypot(food[0] - x, food[1] - y) < .4
        if ate:
            food = (rng.uniform(-6, 6), rng.uniform(-6, 6))
        history.append({'tick': tick, 'x': round(x, 6), 'y': round(y, 6), 'heading': round(heading, 6),
                        'food_x': round(food[0], 6), 'food_y': round(food[1], 6),
                        'left_motor': round(left, 6), 'right_motor': round(right, 6),
                        'mean_activity': round(sum(activity)/len(activity), 6),
                        'saturated_fraction': round(sum(a >= .999 for a in activity)/len(activity), 6),
                        'activity': [round(a, 6) for a in activity], 'ate': ate})
    return history


def import_csv(nodes_path, edges_path, output, limit):
    if limit < 1:
        raise ValueError('limit must be positive')
    with open(nodes_path, newline='') as f:
        nodes = list(csv.DictReader(f))
    if len(nodes) > limit:
        raise ValueError('Node count exceeds limit; explicitly select a smaller circuit instead of silently truncating it')
    ids = {str(n['id']) for n in nodes}
    with open(edges_path, newline='') as f:
        reader = csv.DictReader(f)
        edges = [{'pre': r['body_pre'], 'post': r['body_post'], 'weight': float(r['weight'])}
                 for r in reader if r['body_pre'] in ids and r['body_post'] in ids]
    graph = {'source': 'User-supplied CSV; biological provenance unverified', 'nodes': nodes, 'edges': edges}
    validate_graph(graph)
    Path(output).write_text(json.dumps(graph, indent=2, allow_nan=False))
    print(f'Saved {len(nodes)} neurons and {len(edges)} edges to {output}')


def add_sim_args(parser, out_default, ticks=120):
    parser.add_argument('graph')
    parser.add_argument('--ticks', type=int, default=ticks)
    parser.add_argument('--seed', type=int, default=4)
    parser.add_argument('--out', default=out_default)
    parser.add_argument('--turn-sign', type=float, default=1)
    parser.add_argument('--turn-gain', type=float, default=0.15)
    parser.add_argument('--sensory-sign', type=float, default=1)


def decoder_kwargs(args):
    return {'turn_sign': args.turn_sign, 'turn_gain': args.turn_gain, 'sensory_sign': args.sensory_sign}


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='command', required=True)
    add_sim_args(sub.add_parser('run'), 'trace.json')
    view = sub.add_parser('view')
    add_sim_args(view, 'view.html')
    view.add_argument('--open', action='store_true', help='Open the HTML file in a browser')
    contest = sub.add_parser('contest')
    add_sim_args(contest, 'view.html', ticks=800)
    contest.add_argument('--agents', type=int, default=10)
    contest.add_argument('--foods', type=int, default=3)
    contest.add_argument('--map', dest='map_half', type=float, default=20)
    contest.add_argument('--open', action='store_true', help='Open the HTML file in a browser')
    eco = sub.add_parser('ecosystem')
    add_sim_args(eco, 'view.html', ticks=12000)
    eco.add_argument('--agents', type=int, default=8)
    eco.add_argument('--patches', type=int, default=8)
    eco.add_argument('--map', dest='map_half', type=float, default=20)
    eco.add_argument('--max-age', dest='max_age', type=int, default=None)
    eco.add_argument('--food-rate', dest='food_rate', type=float, default=1.0)
    eco.add_argument('--aging-rate', dest='aging_rate', type=float, default=1.0)
    eco.add_argument('--repro-rate', dest='repro_rate', type=float, default=1.2)
    eco.add_argument('--max-population', dest='max_population', type=int, default=48)
    eco.add_argument('--mutation-rate', dest='mutation_rate', type=float, default=0.9)
    eco.add_argument('--mutation-sigma', dest='mutation_sigma', type=float, default=0.14)
    eco.add_argument('--no-communication', dest='communication', action='store_false')
    eco.add_argument('--no-social-learning', dest='social_learning', action='store_false')
    eco.add_argument('--sense-range', type=float, default=24)
    eco.add_argument('--no-seasons', dest='seasons', action='store_false')
    eco.add_argument('--no-scavenging', dest='scavenging', action='store_false')
    eco.add_argument('--season-length', type=int, default=400)
    eco.add_argument('--record-every', dest='record_every', type=int, default=6)
    eco.add_argument('--open', action='store_true', help='Open the HTML file in a browser')
    imp = sub.add_parser('import-csv')
    imp.add_argument('nodes'); imp.add_argument('edges'); imp.add_argument('output')
    imp.add_argument('--limit', type=int, default=1000)
    a = p.parse_args()
    try:
        if a.command == 'run':
            history = simulate(a.graph, a.ticks, a.seed, **decoder_kwargs(a))
            Path(a.out).write_text(json.dumps(history, indent=2, allow_nan=False))
            print(f'{len(history)} ticks written to {a.out}; food collected: {sum(h["ate"] for h in history)}')
        elif a.command in ('view', 'contest', 'ecosystem'):
            from view import write_viewer
            import webbrowser
            kwargs = decoder_kwargs(a)
            if a.command == 'contest':
                kwargs.update(agents=a.agents, foods=a.foods, map_half=a.map_half)
            elif a.command == 'ecosystem':
                kwargs.update(mode='ecosystem', agents=a.agents, patches=a.patches,
                              map_half=a.map_half, food_rate=a.food_rate,
                              aging_rate=a.aging_rate, repro_rate=a.repro_rate,
                              max_population=a.max_population,
                              mutation_rate=a.mutation_rate, mutation_sigma=a.mutation_sigma,
                              record_every=a.record_every, seasons=a.seasons,
                              scavenging=a.scavenging, season_length=a.season_length,
                              communication=a.communication, sense_range=a.sense_range,
                              social_learning=a.social_learning)
                if a.max_age is not None:
                    kwargs['max_age'] = a.max_age
            output, summary = write_viewer(a.graph, a.ticks, a.seed, a.out, **kwargs)
            print(f'Viewer written to {output}')
            if summary:
                print(summary)
            if a.open:
                webbrowser.open(output.resolve().as_uri())
        else:
            import_csv(a.nodes, a.edges, a.output, a.limit)
    except (ValueError, KeyError, OSError) as exc:
        p.exit(2, f'Error: {exc}\n')


if __name__ == '__main__': main()
