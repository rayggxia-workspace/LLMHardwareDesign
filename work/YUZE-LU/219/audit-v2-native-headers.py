"""Audit the sealed PR260 target signatures against the Block V2 P/U decoders."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re

from route_contract import read_base, digest


def sha(path):
    return sha256(path.read_bytes()).hexdigest()


def proof_entries(path):
    rows = [line.split('  ', 1) for line in path.read_text(encoding='ascii').splitlines()]
    entries = {name: h for h, name in rows}
    assert len(entries) == len(rows), 'duplicate proof entry'
    return entries


def p_header(text):
    guard = re.search(
        r"scope_data\[0\+:32\]!=32'h([0-9a-f]+)\s*\|\|\s*"
        r"scope_data\[32\+:16\]!=16'd(\d+)\s*\|\|\s*"
        r"scope_data\[64\+:32\]!=32'h([0-9a-f]+)", text, re.I)
    assert guard is not None, 'P typed descriptor guard differs'
    schema, size, abi = guard.groups()
    assert int(size) == 128
    return int(schema, 16), int(abi, 16)


def u_header(text):
    guard = re.search(r'wire exec_ok\s*=\s*ENABLE_NATIVE\s*\?\s*'
                      r'\(exec_desc\[0\+:32\]==(\d+)\s*&&', text)
    assert guard is not None, 'U native descriptor guard differs'
    return int(guard[1])


def audit(package, candidate, manifest):
    seal = package / 'proof.sha256'
    signatures_file = package / 'service-signatures.json'
    assert sha(signatures_file) == proof_entries(seal)[signatures_file.name]
    signatures = json.loads(signatures_file.read_bytes())
    base = read_base(candidate / 'base')
    fabric = json.loads((candidate / 'control-fabric').read_bytes())
    target_by_id = {entry['target_id']: entry['controller'] for entry in fabric['targets'].values()}
    assert len(target_by_id) == len(fabric['targets'])
    assemblies = {entry['id']: entry for entry in base['assemblies']}

    rtl = {}
    for group, file in [('p', 'p/p_scope128_decode.sv'), ('u', 'u/pu_native_lc.sv')]:
        item, = [entry for entry in manifest['groups'][group]['inputs'] if entry['file'] == file]
        source = Path(item['origin'])
        assert sha(source) == item['sha256'], f'{file}: source hash differs'
        rtl[group] = source.read_text(encoding='utf-8')

    p_schema, p_abi = p_header(rtl['p'])
    u_schema = u_header(rtl['u'])
    counts = Counter()
    rows = []
    for entry in signatures:
        site = target_by_id[entry['target']]
        view = assemblies[site]['views']['netlist']
        record = dict(entry, group=site, netlist_sha256=base['views'][view]['sha256'])
        if view == 'P.netlist':
            if (entry['schema'], entry['abi']) == (p_schema, p_abi):
                status = 'p_header_matches'
            else:
                status = 'rejected_by_p_scope_header'
        elif view == 'U.netlist':
            # Scope of this check is direct reuse of a PR260 descriptor on
            # the U39 ENABLE_NATIVE EXEC path. Its local record is a different ABI.
            first_word = entry['schema']
            status = 'u_schema_field_matches' if first_word == u_schema else 'rejected_by_u_exec_header'
        else:
            status = 'not_audited'
        counts[status] += entry['calls']
        rows.append(dict(record, status=status))
    return dict(schema='v2-native-dispatch-header-audit/1', base_sha256=digest(base),
                package_proof_sha256=sha(seal), signatures_sha256=sha(signatures_file),
                counts=dict(counts), signatures=rows,
                scope='Direct descriptor reuse only. A header match leaves operands, ABI, completion and data paths to verify.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('package', 'candidate', 'source_manifest', 'output'):
        parser.add_argument(arg, type=Path)
    args = parser.parse_args()
    report = audit(args.package, args.candidate, json.loads(args.source_manifest.read_bytes()))
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report['counts'], sort_keys=True))


if __name__ == '__main__':
    main()
