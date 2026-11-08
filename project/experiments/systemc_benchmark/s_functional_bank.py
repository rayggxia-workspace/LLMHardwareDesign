"""Make an explicitly zero-delay SRAM functional view for activity simulation.

The generated OpenRAM model labels DELAY/T_HOLD arbitrary. They cannot be
used as the characterized TT timing. Remove its output-X hold decoration and
arbitrary read delay in a task-owned copy only. Physical timing/power remains
in the original bank Liberty; this does not qualify frequency or glitches.
"""
import argparse
import hashlib
import json
from pathlib import Path


def create(source, destination):
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    if sha != '6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7':
        raise ValueError('original accepted SRAM functional source changed')
    text = source.read_text()
    replacements = {
        "#(T_HOLD) dout0 = 128'bx;": '// output-X hold decoration omitted in zero-delay activity view',
        'dout0 <= #(DELAY) mem[addr0_reg];': 'dout0 <= mem[addr0_reg];',
        'parameter VERBOSE = 1 ;': 'parameter VERBOSE = 0 ;'}
    for old, new in replacements.items():
        if text.count(old) != 1:
            raise ValueError('unexpected bank source decoration')
        text = text.replace(old, new)
    with destination.open('x') as f:
        f.write(text)
    return {'original_sha256': sha, 'derived_sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
            'changes': replacements, 'timing_qualified': False,
            'boundary': 'functional zero-delay activity view; original characterized Liberty supplies timing/power'}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('source', type=Path)
    p.add_argument('destination', type=Path)
    a = p.parse_args()
    print(json.dumps(create(a.source, a.destination), indent=2))
