"""Reproducible, bounded-memory MaleCNS v1.0 circuit extraction."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request

BASE = 'https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/flat-connectome/'
FILES = {
    'annotations': 'body-annotations-male-cns-v1.0-minconf-0.5.feather',
    'weights': 'connectome-weights-male-cns-v1.0-minconf-0.5.feather',
}
EXPECTED_SHA256 = {
    'annotations': '2177e246113e4cfbf1e7772ec37c6da1955ff22e8063d0b1f833101f99a9a3b2',
    'weights': 'e35da783d1c686b2b58b3b87cd6a403ae43bfcfba8bff28e08ef752c1a56afc1',
}
ATTRIBUTION = ('MaleCNS v1.0: FlyEM, HHMI Janelia; University of Cambridge; '
               'MRC Laboratory of Molecular Biology; Google Research.')


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def arrow():
    try:
        import pyarrow as pa
        import pyarrow.compute as pc
        import pyarrow.feather as feather
        import pyarrow.ipc as ipc
    except ImportError as exc:
        raise ValueError('Install extraction dependencies: python3 -m pip install -r requirements-data.txt') from exc
    return pa, pc, feather, ipc


def download(directory):
    """Atomic downloads. Existing files are kept; extraction hashes every input."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for name in FILES.values():
        target = directory / name
        if target.exists():
            print(f'Using existing {target} (validated and hashed during extraction)')
            continue
        part = target.with_suffix('.part')
        try:
            with urllib.request.urlopen(BASE + name, timeout=60) as r, part.open('wb') as f:
                expected = int(r.headers.get('Content-Length', 0))
                shutil.copyfileobj(r, f, length=4 * 1024 * 1024)
            if expected and part.stat().st_size != expected:
                raise ValueError(f'Incomplete download: {name}')
            part.replace(target)
        finally:
            part.unlink(missing_ok=True)
        print(f'Downloaded {target} ({target.stat().st_size:,} bytes)')


def require_columns(schema, columns, label):
    missing = set(columns) - set(schema.names)
    if missing:
        raise ValueError(f'{label} missing columns: {sorted(missing)}')


def read_annotations(path):
    _, _, feather, _ = arrow()
    table = feather.read_table(path)
    require_columns(table.schema, ['bodyId', 'type', 'instance', 'somaSide', 'superclass'], 'Annotations')
    result = {}
    for n in table.select(['bodyId', 'type', 'instance', 'somaSide', 'superclass']).to_pylist():
        if not isinstance(n['bodyId'], int) or n['bodyId'] <= 0 or n['bodyId'] in result:
            raise ValueError('Annotation IDs must be unique positive integers')
        result[n['bodyId']] = n
    return result


def edge_rows(path, posts, pres=None):
    """Scan Arrow IPC batches, never materializing the entire connection graph."""
    pa, pc, _, ipc = arrow()
    with pa.memory_map(str(path), 'r') as f:
        reader = ipc.open_file(f)
        require_columns(reader.schema, ['body_pre', 'body_post', 'weight'], 'Weights')
        for name in ['body_pre', 'body_post', 'weight']:
            if not pa.types.is_integer(reader.schema.field(name).type):
                raise ValueError(f'Weights column {name} must contain integers')
        for index in range(reader.num_record_batches):
            batch = reader.get_batch(index)
            keep = pc.is_in(batch['body_post'], value_set=pa.array(sorted(posts), type=pa.int64()))
            if pres is not None:
                keep = pc.and_(keep, pc.is_in(batch['body_pre'], value_set=pa.array(sorted(pres), type=pa.int64())))
            for row in batch.filter(keep).select(['body_pre', 'body_post', 'weight']).to_pylist():
                if any(row[k] is None or row[k] <= 0 for k in row):
                    raise ValueError('Selected connections must have positive IDs and weights')
                yield row


def extract(annotations, weights, config):
    if config.get('dataset') != 'male-cns:v1.0':
        raise ValueError('Only male-cns:v1.0 is supported')
    for name in ['top_k_per_output', 'min_selection_weight']:
        if type(config.get(name)) is not int or config[name] < 1:
            raise ValueError(f'{name} must be a positive integer')
    meta = read_annotations(annotations)
    outputs = {i for i, n in meta.items() if n['type'] == config['output_type'] and n['superclass'] == 'descending_neuron'}
    if len(outputs) != 2 or {meta[i]['somaSide'] for i in outputs} != {'L', 'R'}:
        raise ValueError('Output type must resolve to exactly one L and one R descending neuron')
    totals = defaultdict(int)
    for e in edge_rows(weights, outputs):
        n = meta.get(e['body_pre'])
        if n and n['superclass'] == config['input_superclass']:
            totals[e['body_pre'], e['body_post']] += e['weight']
    inputs, selected_by_output = set(), {}
    for output in sorted(outputs):
        eligible = [(pre, w) for (pre, post), w in totals.items()
                    if post == output and w >= config['min_selection_weight']]
        chosen = sorted(eligible, key=lambda p: (-p[1], p[0]))[:config['top_k_per_output']]
        if not chosen:
            raise ValueError(f'No qualifying visual inputs for output {output}')
        inputs.update(pre for pre, _ in chosen)
        selected_by_output[str(output)] = [{'id': str(pre), 'weight': w} for pre, w in chosen]
    if inputs & outputs:
        raise ValueError('Input and output sets must be disjoint')
    ids = inputs | outputs
    nodes = []
    for i in sorted(ids):
        n = meta[i]
        if n['somaSide'] not in ['L', 'R']:
            raise ValueError(f'No explicit L/R soma annotation for selected neuron {i}')
        nodes.append({'id': str(i), 'role': 'motor' if i in outputs else 'sensory',
                      'side': {'L': 'left', 'R': 'right'}[n['somaSide']],
                      'type': n['type'], 'instance': n['instance'],
                      'superclass': n['superclass'], 'somaSide': n['somaSide']})
    # Preserve ALL connections within the chosen nodes, including weak and recurrent edges.
    induced = defaultdict(int)
    for e in edge_rows(weights, ids, ids):
        induced[e['body_pre'], e['body_post']] += e['weight']
    edges = [{'pre': str(pre), 'post': str(post), 'weight': w}
             for (pre, post), w in sorted(induced.items())]
    provenance = {
        'dataset': 'male-cns:v1.0', 'kind': 'local-file-subgraph-unverified',
        'license': 'CC-BY-4.0', 'license_url': 'https://creativecommons.org/licenses/by/4.0/',
        'attribution': ATTRIBUTION, 'project_url': 'https://male-cns.janelia.org/',
        'sources': {key: {'url': BASE + FILES[key], 'sha256': digest(path), 'bytes': Path(path).stat().st_size}
                    for key, path in [('annotations', annotations), ('weights', weights)]},
        'source_verification': 'Hashes identify the supplied local files; compare with the checked-in real-data report. Hashing alone does not prove origin.',
        'selection': config, 'selected_inputs_by_output': selected_by_output,
        'modifications': 'Selected nodes; retained all induced directed edges; summed duplicate pairs. Raw integer synapse counts retained.',
    }
    return {'source': f'MaleCNS v1.0 derived {config["output_type"]} circuit (experimental mapping)',
            'provenance': provenance,
            'assumptions': [
                'Sensory/motor are simulator interface roles, not biological cell classifications.',
                'Visual projection neurons are driven directly; retinal and upstream processing is omitted.',
                'Soma side maps to virtual sensor and output side; this is not validated functional laterality.',
                'No neurotransmitter signs or physiological parameters are inferred from wiring.',
            ], 'nodes': nodes, 'edges': edges}


def verify_release(graph):
    for key, expected in EXPECTED_SHA256.items():
        if graph['provenance']['sources'][key]['sha256'] != expected:
            raise ValueError(f'{key} SHA-256 does not match the pinned official release; refusing to label it MaleCNS data')
    graph['provenance']['kind'] = 'official-file-derived-subgraph'
    graph['provenance']['source_verification'] = 'Both inputs match SHA-256 hashes measured from official public downloads on 2026-09-20; these are project pins, not publisher-signed hashes.'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    d = sub.add_parser('download', help='Download ~1.1 GB of official public files; no token required')
    d.add_argument('--directory', default='data/raw')
    e = sub.add_parser('extract')
    e.add_argument('--directory', default='data/raw')
    e.add_argument('--config', default='configs/dng13.json')
    e.add_argument('--out', default='circuits/dng13.json')
    args = parser.parse_args()
    try:
        if args.command == 'download':
            download(args.directory)
        else:
            graph = extract(Path(args.directory)/FILES['annotations'], Path(args.directory)/FILES['weights'], json.loads(Path(args.config).read_text()))
            verify_release(graph)
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(graph, indent=2, allow_nan=False) + '\n')
            print(f'Extracted {len(graph["nodes"])} neurons and {len(graph["edges"])} connections -> {out}')
    except (ValueError, OSError) as exc:
        parser.exit(2, f'Error: {exc}\n')


if __name__ == '__main__':
    main()
