"""Self-contained HTML playback for a simulation trace. No extra packages."""
import json
from pathlib import Path
from sim import simulate, validate_decoder

TEMPLATE = Path(__file__).with_name('viewer.html')
PLACEHOLDER = '__PLAYBACK_JSON__'


def circuit_kind(graph):
    source = str(graph.get('source', ''))
    provenance = graph.get('provenance') if isinstance(graph.get('provenance'), dict) else {}
    kind = str(provenance.get('kind', ''))
    if 'NOT MaleCNS' in source or 'synthetic' in source.lower():
        return 'synthetic'
    if kind == 'official-file-derived-subgraph' or source.startswith('MaleCNS'):
        return 'malecns-derived'
    return 'unverified'


def playback_document(path, ticks, seed, **decoder_args):
    path = Path(path)
    graph = json.loads(path.read_text())
    decoder = validate_decoder(**{key: decoder_args[key] for key in decoder_args
                                 if key in {'turn_sign', 'turn_gain', 'turn_clip', 'speed_gain', 'sensory_sign'}})
    history = simulate(path, ticks, seed, **decoder)
    provenance = graph.get('provenance') if isinstance(graph.get('provenance'), dict) else {}
    nodes = []
    for node in graph['nodes']:
        nodes.append({
            'id': str(node['id']),
            'role': node['role'],
            'side': node['side'],
            'label': node.get('instance') or node.get('type') or str(node['id']),
        })
    return {
        'kind': circuit_kind(graph),
        'source': graph.get('source'),
        'dataset': provenance.get('dataset'),
        'license': provenance.get('license'),
        'attribution': provenance.get('attribution'),
        'assumptions': graph.get('assumptions') or [
            'Toy bounded rate model. Sensory/motor labels are simulator interface roles.'
        ],
        'decoder': decoder,
        'seed': seed,
        'graph': str(path),
        'nodes': nodes,
        'ticks': history,
    }


def render_viewer(payload):
    template = TEMPLATE.read_text()
    if template.count(PLACEHOLDER) != 1:
        raise ValueError('viewer.html must contain the playback placeholder exactly once')
    encoded = json.dumps(payload, allow_nan=False, separators=(',', ':')).replace('<', '\\u003c')
    return template.replace(PLACEHOLDER, encoded)


def write_viewer(path, ticks, seed, output, **decoder_args):
    html = render_viewer(playback_document(path, ticks, seed, **decoder_args))
    output = Path(output)
    output.write_text(html)
    return output
