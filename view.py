"""Self-contained HTML playback for a simulation trace. No extra packages."""
import json
from pathlib import Path
from sim import simulate, validate_decoder
from contest import simulate_contest, summarize_contest

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
    return _document(path, graph, decoder, seed, history)


def contest_document(path, ticks, seed, **kwargs):
    path = Path(path)
    graph = json.loads(path.read_text())
    decoder_keys = {key: kwargs[key] for key in kwargs
                    if key in {'turn_sign', 'turn_gain', 'turn_clip', 'speed_gain', 'sensory_sign'}}
    decoder = validate_decoder(**decoder_keys)
    contest_keys = {key: kwargs[key] for key in kwargs
                    if key in {'agents', 'foods', 'map_half', 'drive_enabled', 'disconnected', 'shuffle_seed'}}
    result = simulate_contest(path, ticks, seed, **decoder, **contest_keys)
    document = _document(path, graph, decoder, seed, result['ticks'])
    document.update({
        'mode': 'contest',
        'rules': result['rules'],
        'ranking': result['ranking'],
        'winner': result['winner'],
        'assumptions': (graph.get('assumptions') or []) + [
            'Contest energy, map size, and scarce pellets are engineered scoring rules, not fly physiology.',
            'All flies share the same circuit and decoder; they differ only by spawn pose.',
        ],
    })
    return document


def _document(path, graph, decoder, seed, history):
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


def write_viewer(path, ticks, seed, output, **kwargs):
    if kwargs.get('agents', 1) > 1:
        payload = contest_document(path, ticks, seed, **kwargs)
        summary = summarize_contest(payload)
    else:
        payload = playback_document(path, ticks, seed, **kwargs)
        summary = None
    output = Path(output)
    output.write_text(render_viewer(payload))
    return output, summary
