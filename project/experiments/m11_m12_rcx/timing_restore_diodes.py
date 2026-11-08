"""Restore physical diode instances omitted by logical Verilog export.

Identity, cell, pin and connection come from the matching final SPEF CONN.
No transistor, R or C is invented. Original source files remain read-only.
"""
import argparse
import json
import os
from pathlib import Path
import re

from timing_native import sha
from timing_prepare import records, esc


def declarations(text):
    found = {}
    for m in re.finditer(r'\b(?:input|output|inout|wire)\s*(\[\s*-?\d+\s*:\s*-?\d+\s*\])?\s*(\\\S+|[A-Za-z_$][\w$]*)\s*;', text):
        name = m[2].lstrip('\\')
        found[name] = tuple(map(int, re.findall(r'-?\d+', m[1]))) if m[1] else None
    return found


def expression(name, declared):
    # SPEF escapes bracket characters that are literal parts of identifiers.
    name = re.sub(r'\\(.)', r'\1', name)
    if name in declared: return esc(name)
    m = re.fullmatch(r'(.*)\[(-?\d+)\]', name)
    assert m and m[1] in declared and declared[m[1]] is not None, ('Undeclared native signal', name)
    bounds = declared[m[1]]; bit = int(m[2]); assert min(bounds) <= bit <= max(bounds)
    return esc(m[1]) + '[' + m[2] + ']'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepared', type=Path, required=True)
    p.add_argument('--out', type=Path, default=Path(os.environ.get('TIMING_OUT', '.')) / 'result')
    a = p.parse_args(); a.out.mkdir()
    meta = json.loads((a.prepared / 'prepare.json').read_text())
    modules = {}
    for filename in meta['full_verilog']:
        text = Path(filename).read_text(); names = re.findall(r'(?m)^module\s+(\S+)', text)
        assert len(names) == 1 and names[0] not in modules
        modules[names[0]] = (filename, text)
    inventories = []
    updated = {}
    for spef in sorted({path for _, path in meta['full_spefs']}):
        with Path(spef).open() as stream:
            for line in stream:
                if line.startswith('*DESIGN '): module = line.split('"')[1]; break
        assert module in modules, module
        filename, text = modules[module]
        declared = declarations(text); extra = {}; section = None
        present = {n.lstrip('\\') for n in re.findall(r'\bANTENNA_X1\s+(\\\S+|[A-Za-z_$][\w$]*)\s*\(', text)}
        for names, header, alias, rows in records(Path(spef)):
            net = names[alias]
            for line in rows:
                w = line.split()
                if not w: continue
                if w[0] in ('*CONN', '*CAP', '*RES', '*END'): section = w[0]
                if section == '*CONN' and w[0] == '*I' and '*D' in w and w[w.index('*D') + 1] == 'ANTENNA_X1':
                    instance, pin = w[1].rsplit(':', 1); instance = names.get(instance, instance)
                    assert pin == 'A'
                    if instance in present: continue
                    assert instance not in extra or extra[instance] == net
                    extra[instance] = net
        if extra:
            additions = ['ANTENNA_X1 ' + esc(n) + '(.A(' + expression(net, declared) + '));' for n, net in sorted(extra.items())]
            assert text.count('endmodule') == 1
            fixed = text.replace('endmodule', '\n// Existing physical diodes restored from the matching final SPEF.\n' + '\n'.join(additions) + '\nendmodule')
            target = a.out / (module + '.v'); target.write_text(fixed)
            updated[filename] = str(target.resolve())
        inventories.append(dict(module=module, verilog=filename, verilog_sha256=sha(filename), spef=spef,
                                spef_sha256=sha(spef), restored_diodes=len(extra),
                                connections=extra, restored_verilog=updated.get(filename, filename)))
    meta['full_verilog'] = [updated.get(f, f) for f in meta['full_verilog']]
    meta['parent_prepare'] = str(a.prepared)
    meta['parent_prepare_sha256'] = sha(a.prepared / 'prepare.json')
    meta['restored_physical_diodes'] = sum(x['restored_diodes'] for x in inventories)
    assert meta['restored_physical_diodes'] > 0
    (a.out / 'prepare.json').write_text(json.dumps(meta, indent=2) + '\n')
    (a.out / 'diode-restoration.json').write_text(json.dumps(inventories, indent=2) + '\n')
    print(json.dumps(dict(modules=len(inventories), restored_diodes=meta['restored_physical_diodes'])), flush=True)


if __name__ == '__main__': main()
