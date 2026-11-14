"""Externally supplied SRAM parameters and aligned native-word transactions."""

from dataclasses import dataclass
from hashlib import sha256
import json


WORD_BYTES = 16
WORD_BITS = WORD_BYTES * 8


def words_per_beat(bits):
    if type(bits) is not int or bits <= 0 or bits % WORD_BITS:
        raise ValueError(f'SRAM width must be a positive multiple of {WORD_BITS} bits')
    return bits // WORD_BITS


@dataclass(frozen=True)
class Sram:
    assembly: str
    capacity_bytes: int
    read_bits: int
    write_bits: int

    def __post_init__(self):
        if not isinstance(self.assembly, str) or not self.assembly:
            raise ValueError('SRAM must name its physical assembly')
        if (type(self.capacity_bytes) is not int or self.capacity_bytes <= 0
                or self.capacity_bytes % WORD_BYTES):
            raise ValueError(f'SRAM capacity must be a positive multiple of {WORD_BYTES} bytes')
        words_per_beat(self.read_bits)
        words_per_beat(self.write_bits)

    def beats(self, start_word, word_count, *, write, service_bits):
        """Return (first_word, count) per transaction, without scheduling ACKs."""
        if type(write) is not bool:
            raise ValueError('SRAM operation must specify read or write')
        capacity = self.capacity_bytes // WORD_BYTES
        if (type(start_word) is not int or type(word_count) is not int
                or not 0 <= start_word <= start_word + word_count <= capacity):
            raise ValueError('SRAM span is outside its instance capacity')
        port_words = words_per_beat(self.write_bits if write else self.read_bits)
        service_words = words_per_beat(service_bits)
        result = []
        end = start_word + word_count
        while start_word < end:
            size = min(end - start_word, port_words - start_word % port_words,
                       service_words - start_word % service_words)
            result.append((start_word, size))
            start_word += size
        return result


def load_sram_profile(path, base_sha256, assemblies):
    raw = path.read_bytes()
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError('SRAM parameters must be a JSON object')
    if data.get('base_sha256') != base_sha256:
        raise ValueError('SRAM parameters refer to a different base')
    rows = data.get('sram')
    if not isinstance(rows, dict) or not rows:
        raise ValueError('SRAM parameters need named instances')
    instances = {}
    for name, row in rows.items():
        if not name.strip() or not isinstance(row, dict):
            raise ValueError('invalid named SRAM instance')
        try:
            instance = Sram(**row)
        except (TypeError, ValueError) as exc:
            raise ValueError(f'{name}: {exc}') from exc
        if instance.assembly not in assemblies:
            raise ValueError(f'{name}: SRAM assembly does not exist on this base')
        instances[name] = instance
    return instances, sha256(raw).hexdigest()

