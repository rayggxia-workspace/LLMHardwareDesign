"""Rename only synthetic parent scalar ports to unambiguous identifiers.

Native macro ports, physical nets and all RC stay unchanged. The logical
Verilog fixture used escaped scalar names containing brackets; those conflict
with SPEF bus-name resolution in the OpenDB network provider. Hex-encoding
these synthetic parent names is an exact renaming, not a design change.
"""
import argparse
import json
import os
from pathlib import Path

from timing_native import sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepared', type=Path, required=True)
    p.add_argument('--driver-proof', type=Path, required=True)
    p.add_argument('--out', type=Path, default=Path(os.environ.get('TIMING_OUT', '.')) / 'result')
    a = p.parse_args(); a.out.mkdir()
    d = json.loads((a.prepared / 'prepare.json').read_text())
    driver = json.loads(a.driver_proof.read_text())
    assert driver['prepared_sha256'] == sha(a.prepared / 'prepare.json')
    original = Path(d['harness']); text = original.read_text()
    aliases = {}
    for old in d['external']:
        inst, pin = old[4:].split('_', 1)
        new = 'ext_' + inst + '_p' + pin.encode().hex()
        assert new not in aliases.values()
        token = '\\' + old + ' '
        assert text.count(token) >= 3, (old, text.count(token))
        text = text.replace(token, new + ' ')
        aliases[old] = new
    target = a.out / 'harness.v'; target.write_text(text)
    d['external'] = {aliases[n]: v for n, v in d['external'].items()}
    d['external_port_aliases'] = aliases
    d['harness'] = str(target.resolve())
    d['parent_prepare'] = str(a.prepared)
    d['parent_prepare_sha256'] = sha(a.prepared / 'prepare.json')
    (a.out / 'prepare.json').write_text(json.dumps(d, indent=2) + '\n')
    driver['parent_driver_proof'] = str(a.driver_proof)
    driver['parent_driver_proof_sha256'] = sha(a.driver_proof)
    driver['prepared'] = str(a.out.resolve())
    driver['prepared_sha256'] = sha(a.out / 'prepare.json')
    driver['reuse_reason'] = 'Only synthetic external parent identifiers renamed; native ports, word connections and physical driver connectivity unchanged.'
    (a.out / 'driver-proof.json').write_text(json.dumps(driver, indent=2) + '\n')
    (a.out / 'port-renaming.json').write_text(json.dumps(dict(original_harness=str(original), original_harness_sha256=sha(original),
                                                          harness_sha256=sha(target), aliases=aliases,
                                                          native_and_upper_rc_changed=False), indent=2) + '\n')
    print(json.dumps(dict(renamed_parent_ports=len(aliases), native_and_upper_rc_changed=False)), flush=True)


if __name__ == '__main__': main()
