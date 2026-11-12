"""Qualified single-word scatter service of the #251 programmed FFN."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Fragment:
    client: int
    way: int
    first: int
    words: int

    @property
    def scratch(self):
        return 896 + 16 * self.way

    @property
    def ring(self):
        return 720 + 64 * self.way

    def destination(self, word):
        return self.ring + (self.first // 4 + 6 * (word // 2) + word % 2) % 64


def stripe_fragments(first, width):
    if width not in (64, 128, 192) or first % 8 or not 0 <= first <= 11008 - width:
        raise ValueError('unsupported Gate/Up stripe geometry')
    groups, extra = divmod(width // 8, 3)
    return tuple(Fragment(client, way, first + 8 * client, 2 * (groups + (client < extra)))
                 for way in range(2) for client in range(3))


def scatter_service(fragments, mode):
    """Return the registered service recipe, independent of measured latency."""
    if mode not in (0, 1):
        raise ValueError('unknown FFN fixture pressure mode')
    phases = []

    def phase(name, ticks, resource=None, *, client=None, response=False):
        item = {'kind': name, 'ticks': ticks, 'claims': {resource: 1} if resource else {}}
        if mode and client is not None:
            period, closed, step = (11, 4, 3) if response else (7, 2, 2)
            item['ready_window'] = {'period': period, 'closed': closed, 'offset': step * client}
        phases.append(item)

    for index, fragment in enumerate(fragments):
        prefix = f'fragment{index}'
        phase(f'{prefix}.start', 2)
        source = fragment.client
        for word in range(fragment.words):
            name = f'{prefix}.word{word}'
            phase(f'{name}.read', 1, f'P{source}.S.request', client=source)
            phase(f'{name}.read_pipeline', 1)
            phase(f'{name}.response', 1, f'P{source}.S.response', client=source, response=True)
            phase(f'{name}.write', 1, 'P0.S.request', client=0)
            phase(f'{name}.write_pipeline', 1)
            phase(f'{name}.ack', 1, 'P0.S.response', client=0, response=True)
            phase(f'{name}.advance', 1)
        phase(f'{prefix}.done', 1)
    phase('commit', 1)
    return {'ticks': sum(item['ticks'] for item in phases), 'claims': {},
            'hold_claims': {'scatter': 1}, 'phases': phases}
