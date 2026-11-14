"""Check ordered hardware handshakes for a runtime-index Gather page."""

EVENT_FIELDS = {
    'NATIVE_GATHER_CALL': ('step', 'page', 'generation', 'target', 'cycle'),
    'NATIVE_GATHER_RESERVE': ('step', 'page', 'generation', 'word', 'cycle'),
    'NATIVE_GATHER_INDEX_ACK': ('step', 'page', 'generation', 'word', 'data', 'cycle'),
    'NATIVE_GATHER_INDEX_READ': ('step', 'page', 'generation', 'word', 'cycle'),
    'NATIVE_GATHER_INDEX_DATA': ('step', 'page', 'generation', 'word', 'data', 'cycle'),
}
EVENTS = tuple(EVENT_FIELDS)


def parse_event(line):
    name, *fields = line.split()
    keys = EVENT_FIELDS[name]
    parts = [field.split('=', 1) for field in fields]
    if len(parts) != len(keys) or any(len(pair) != 2 for pair in parts):
        raise ValueError(f'malformed {name}')
    if tuple(key for key, _ in parts) != keys:
        raise ValueError(f'malformed {name}')
    return name, {key: int(value, 16 if key == 'data' else 10) for key, value in parts}


class GatherIndexEvidence:
    """Audit one page between the real MC start and its successful terminal."""

    def __init__(self, *, step, page, generation, target, word, token, launch_cycle):
        if not (0 <= word < 1024 and 0 < generation < 2**32 and 0 <= token < 2**32):
            raise ValueError('invalid runtime index binding')
        self.identity = step, page, generation
        self.target = target
        self.word = word
        self.data = token << 64
        self.cycle = launch_cycle
        self.observed = {}

    def consume(self, line):
        name, row = parse_event(line)
        if (row['step'], row['page'], row['generation']) != self.identity:
            raise ValueError('Gather handshake has wrong page identity')
        if row['cycle'] <= self.cycle:
            raise ValueError('Gather handshakes are not strictly ordered')
        position = len(self.observed)
        if position >= len(EVENTS) or name != EVENTS[position]:
            raise ValueError('Gather handshake is duplicate, missing, or out of order')
        if (row.get('target', self.target) != self.target or row.get('word', self.word) != self.word
                or row.get('data', self.data) != self.data):
            raise ValueError('Gather target, index word or SRAM data differs')
        self.cycle = row['cycle']
        self.observed[name] = self.cycle

    def finish(self, terminal_cycle):
        if tuple(self.observed) != EVENTS or terminal_cycle <= self.cycle:
            raise ValueError('Gather terminal lacks complete index evidence')
        return dict(self.observed)


def load_bindings(path, expected_sha256, program, phases):
    from hashlib import sha256
    import json

    raw = path.read_bytes()
    if sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('changed phase bindings')
    binding = json.loads(raw)
    rows = binding['phases']
    if (binding['schema'] != 'native-request-phase-bindings/1'
            or binding['request_sha256'] != program['deployment_sha256']
            or binding['total_pages'] != program['expected_pages']
            or [row['graph_sha256'] for row in rows] != [row['graph_sha256'] for row in phases]):
        raise ValueError('post-CALL Gather bindings differ from the audited graphs')
    result = {}
    generation = 0
    for step, phase in enumerate(rows):
        count = phase['pages']
        index = phase['index']
        if phase['step'] != step or count <= 0 or phase['first_generation'] != generation+1:
            raise ValueError('wrong post-CALL Gather phase generation')
        if index is not None:
            if (step == 0 or not 0 <= index['page'] < count or not 0 <= index['target'] < 9
                    or index['generation'] != generation+index['page']+1):
                raise ValueError('invalid post-CALL Gather page')
            result[step, index['page']] = index
        generation += count
    if generation != program['expected_pages'] or len(result) != binding['feedback_edges']:
        raise ValueError('incomplete post-CALL Gather binding')
    return result
