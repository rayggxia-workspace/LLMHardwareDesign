"""Recover only the 29 missing literal-backslash original SPEF references."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import re


def clean(name):
    return re.sub(r'\\(.)', r'\1', name)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    config = json.loads(Path(os.environ['LOWER_CONFIG']).read_text())
    index = int(os.environ['LOWER_INDEX'])
    if 'patch_cases' in config:
        kind = config['patch_cases'][index]['kind']
        folder = Path(config['patch_cases'][index]['inventory'])
    else:
        kind = ['C0', 'F0', 'U0'][index]
        folder = Path(config['inventories'][kind])
    meta = json.loads((folder / 'inventory.json').read_text())
    assert sha(folder / 'net-inventory.jsonl.gz') == meta['inventory_sha256']
    by_name = {}
    with gzip.open(folder / 'net-inventory.jsonl.gz', 'rt') as f:
        for line in f:
            row = json.loads(line)
            by_name[row['name']] = row
    normalized = {clean(n): n for n in by_name}
    assert len(normalized) == len(by_name)
    source = Path(meta['source_spef'])
    mapped, recovered = {}, {}
    active, mode = None, None
    h = hashlib.sha256()
    with source.open('rb') as f:
        for raw in f:
            h.update(raw)
            line = raw.decode().strip()
            if line.startswith('*C_UNIT '):
                _, v, unit = line.split()
                cap = float(v) * {'FF': 1., 'PF': 1000.}[unit]
            elif line.startswith('*R_UNIT '):
                _, v, unit = line.split()
                resistance = float(v) * {'OHM': 1., 'KOHM': 1000.}[unit]
            elif line == '*NAME_MAP':
                mode = 'names'
            elif line.startswith('*D_NET '):
                _, token, value = line.split()
                name = mapped.get(token, clean(token))
                candidates = {n for n in [normalized.get(name), normalized.get(clean(name))] if n is not None}
                assert len(candidates) <= 1
                resolved = next(iter(candidates)) if candidates else None
                active = None
                if resolved is not None and 'original' not in by_name[resolved]:
                    assert resolved not in recovered
                    active = dict(original_declared_cap_ff=float(value) * cap,
                                  original_ground_cap_ff=0., original_cc_entries_ff=0.,
                                  original_resistance_sum_ohm=0., original_resistance_edges=0)
                    recovered[resolved] = dict(original_spef_net=name, original=active)
                mode = None
            elif line == '*CAP':
                mode = 'cap'
            elif line == '*RES':
                mode = 'res'
            elif line.startswith('*') and mode == 'names' and re.match(r'^\*\d+\s', line):
                token, name = line.split(maxsplit=1)
                mapped[token] = clean(name)
            elif line.startswith('*'):
                mode = None
            elif active is not None and line and mode == 'cap':
                values = line.split()
                assert len(values) in (3, 4)
                key = 'original_ground_cap_ff' if len(values) == 3 else 'original_cc_entries_ff'
                active[key] += float(values[-1]) * cap
            elif active is not None and line and mode == 'res':
                values = line.split()
                assert len(values) == 4
                active['original_resistance_sum_ohm'] += float(values[-1]) * resistance
                active['original_resistance_edges'] += 1
    assert h.hexdigest() == meta['source_spef_sha256']
    assert len(recovered) == meta['missing_spef_geometry_count']
    out = Path(os.environ['LOWER_OUT'])
    out.mkdir()
    result = dict(kind=kind, inventory=str(folder), inventory_metadata_sha256=sha(folder / 'inventory.json'),
                  original_spef=str(source), original_spef_sha256=h.hexdigest(),
                  recovered=recovered, recovered_count=len(recovered),
                  scope='Original reference metadata only. Literal backslashes retained; no geometry or parasitic extraction repeated.')
    (out / 'original-patch.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(kind=kind, recovered=len(recovered))), flush=True)


if __name__ == '__main__':
    main()
