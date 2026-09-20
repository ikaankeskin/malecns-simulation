"""Small connectome-driven foraging experiment; dynamics are exploratory."""
import argparse
import csv
import json
import math
import random
from pathlib import Path


def load_graph(path):
    graph = json.loads(Path(path).read_text())
    nodes = graph['nodes']
    ids = {str(node['id']): i for i, node in enumerate(nodes)}
    incoming = [[] for _ in nodes]
    for edge in graph['edges']:
        source, target = ids[str(edge['pre'])], ids[str(edge['post'])]
        incoming[target].append((source, min(float(edge['weight']), 100) / 100))
    return nodes, incoming


def simulate(path, ticks, seed):
    nodes, incoming = load_graph(path)
    rng = random.Random(seed)
    activity = [0.0] * len(nodes)
    x = y = 0.0
    heading = 0.0
    food = (5.0, 3.0)
    history = []
    sensory = [i for i, n in enumerate(nodes) if n.get('role') == 'sensory']
    motors = [i for i, n in enumerate(nodes) if n.get('role') == 'motor']
    if not sensory or not motors:
        raise ValueError('Graph needs at least one sensory and one motor neuron (role field).')
    for tick in range(ticks):
        bearing = math.atan2(food[1] - y, food[0] - x) - heading
        bearing = math.atan2(math.sin(bearing), math.cos(bearing))
        distance = math.hypot(food[0] - x, food[1] - y)
        stimulus = max(0.0, 1.0 - distance / 12.0)
        # Directional sensory input and motor interpretation are explicit model assumptions.
        drives = [0.0] * len(nodes)
        for i in sensory:
            side = nodes[i].get('side', 'center')
            drives[i] = stimulus * (1 + (math.sin(bearing) if side == 'left' else -math.sin(bearing) if side == 'right' else 0))
        nxt = [0.0] * len(nodes)
        for i in range(len(nodes)):
            signal = sum(activity[j] * w for j, w in incoming[i])
            nxt[i] = max(0.0, min(1.0, .75 * activity[i] + .25 * (signal + drives[i])))
        activity = nxt
        left = sum(activity[i] for i in motors if nodes[i].get('side') == 'left')
        right = sum(activity[i] for i in motors if nodes[i].get('side') == 'right')
        heading += max(-.3, min(.3, (right - left) * .15))
        speed = .03 + .1 * min(1, left + right)
        x += speed * math.cos(heading)
        y += speed * math.sin(heading)
        ate = math.hypot(food[0] - x, food[1] - y) < .4
        if ate:
            food = (rng.uniform(-6, 6), rng.uniform(-6, 6))
        history.append({'tick': tick, 'x': round(x, 3), 'y': round(y, 3), 'heading': round(heading, 3), 'food_x': round(food[0], 3), 'food_y': round(food[1], 3), 'left_motor': round(left, 4), 'right_motor': round(right, 4), 'ate': ate})
    return history


def import_csv(nodes_path, edges_path, output, limit):
    """Import an exported MaleCNS subset: IDs and body_pre/body_post/weight."""
    with open(nodes_path, newline='') as f:
        nodes = list(csv.DictReader(f))
    nodes = nodes[:limit]
    ids = {str(n['id']) for n in nodes}
    if not ids:
        raise ValueError('No nodes selected')
    with open(edges_path, newline='') as f:
        reader = csv.DictReader(f)
        edges = [{'pre': r['body_pre'], 'post': r['body_post'], 'weight': float(r['weight'])} for r in reader if r['body_pre'] in ids and r['body_post'] in ids]
    Path(output).write_text(json.dumps({'source': 'MaleCNS v1.0 subset; see README for provenance', 'nodes': nodes, 'edges': edges}, indent=2))
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
    imp.add_argument('nodes')
    imp.add_argument('edges')
    imp.add_argument('output')
    imp.add_argument('--limit', type=int, default=1000)
    a = p.parse_args()
    if a.command == 'run':
        history = simulate(a.graph, a.ticks, a.seed)
        Path(a.out).write_text(json.dumps(history, indent=2))
        print(f'{len(history)} ticks written to {a.out}; food collected: {sum(h["ate"] for h in history)}')
    else:
        import_csv(a.nodes, a.edges, a.output, a.limit)


if __name__ == '__main__':
    main()
