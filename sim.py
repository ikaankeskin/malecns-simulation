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


def simulate(path, ticks, seed, *, drive_enabled=True, disconnected=False,
             shuffle_seed=None, initial_food=(5.0, 3.0)):
    if type(ticks) is not int or ticks < 1:
        raise ValueError('ticks must be a positive integer')
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
        drives = [0.0] * len(circuit.nodes)
        for i, n in enumerate(circuit.nodes):
            if n['role'] == 'sensory':
                side = n['side']
                drives[i] = stimulus * (1 + (math.sin(bearing) if side == 'left' else -math.sin(bearing) if side == 'right' else 0))
        activity = circuit.step(drives)
        left, right = circuit.motors()
        heading += max(-.3, min(.3, (right - left) * .15))
        # No independent locomotion bias: silencing the circuit stops movement.
        speed = .13 * min(1, left + right)
        x += speed * math.cos(heading)
        y += speed * math.sin(heading)
        ate = math.hypot(food[0] - x, food[1] - y) < .4
        if ate:
            food = (rng.uniform(-6, 6), rng.uniform(-6, 6))
        history.append({'tick': tick, 'x': round(x, 6), 'y': round(y, 6), 'heading': round(heading, 6),
                        'food_x': round(food[0], 6), 'food_y': round(food[1], 6),
                        'left_motor': round(left, 6), 'right_motor': round(right, 6),
                        'mean_activity': round(sum(activity)/len(activity), 6),
                        'saturated_fraction': round(sum(a >= .999 for a in activity)/len(activity), 6), 'ate': ate})
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


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='command', required=True)
    run = sub.add_parser('run')
    run.add_argument('graph')
    run.add_argument('--ticks', type=int, default=120)
    run.add_argument('--seed', type=int, default=4)
    run.add_argument('--out', default='trace.json')
    imp = sub.add_parser('import-csv')
    imp.add_argument('nodes'); imp.add_argument('edges'); imp.add_argument('output')
    imp.add_argument('--limit', type=int, default=1000)
    a = p.parse_args()
    try:
        if a.command == 'run':
            history = simulate(a.graph, a.ticks, a.seed)
            Path(a.out).write_text(json.dumps(history, indent=2, allow_nan=False))
            print(f'{len(history)} ticks written to {a.out}; food collected: {sum(h["ate"] for h in history)}')
        else:
            import_csv(a.nodes, a.edges, a.output, a.limit)
    except (ValueError, KeyError, OSError) as exc:
        p.exit(2, f'Error: {exc}\n')


if __name__ == '__main__': main()
