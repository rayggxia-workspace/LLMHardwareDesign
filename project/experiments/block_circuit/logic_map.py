"""Server-only logic mapping, explicitly excluding both shared memory wrappers."""
import argparse
import json
import re
import time
import traceback
from pathlib import Path
from run import ROOT, RTL, command, put, sha


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--binding', type=Path, required=True)
    p.add_argument('--library', type=Path, required=True)
    p.add_argument('--provenance', type=Path, required=True)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--mode', type=int, choices=[0, 1], required=True)
    p.add_argument('--prefix', required=True)
    a = p.parse_args()
    binding = json.loads(a.binding.read_text())
    for name, digest in binding['sources'].items():
        if sha(ROOT/name) != digest:
            raise ValueError('frozen source differs: '+name)
    provenance = json.loads(a.provenance.read_text())
    entry = next(x for x in provenance['files'] if x['path'].endswith('.lib'))
    if sha(a.library) != entry['sha256'] or a.library.stat().st_size != entry['bytes']:
        raise ValueError('exact official fixed-version library required')
    a.out.mkdir(exist_ok=False, parents=True)
    m = {'schema': 'block-logic-map80-v1', 'status': 'ERROR',
         'source': binding, 'mode': a.mode, 'library': provenance,
         'excluded': ['entire common ram128 frame wrapper and 512B array',
                      'entire common lut32 wrapper and 128KiB array'],
         'limits': ['Non-manufacturable Nangate45 research model, not a target process.',
                    'Logic area only; no SRAM/ROM macro, placement, wiring, CTS, STA or clock frequency.',
                    'No same-area claim: external interfaces and debug counters are retained.']}
    started = time.monotonic()
    try:
        (a.out/'rom.hex').write_bytes((a.input/'rom.hex').read_bytes())
        sv = [RTL/n for n in ('byte_alu.sv', 'ram128.sv', 'wide_engine.sv', 'memory_link.sv', 'wide_block.sv')]
        script = ('read_liberty -lib '+str(a.library)+'\nread_verilog -sv '+' '.join(map(str, sv))+
                  '\nhierarchy -top wide_block -chparam LOCAL '+str(a.mode)+
                  '\nblackbox ram128 lut32\nsynth -top wide_block -flatten\n'+
                  'dfflibmap -liberty '+str(a.library)+'\nabc -liberty '+str(a.library)+
                  '\nclean\ncheck -assert\ntee -o '+str(a.out/'stat.json')+
                  ' stat -liberty '+str(a.library)+' -json\nwrite_json '+str(a.out/'mapped.json')+'\n')
        (a.out/'map.ys').write_text(script, encoding='utf-8')
        command(a.out, 'mapping', ['yosys', '-s', a.out/'map.ys'], json.loads(a.prefix), cwd=a.out)
        # Independently sum the emitted actual top-level instances against Liberty
        # area, rather than trusting a producer-written area or timing label.
        text = a.library.read_text()
        starts = list(re.finditer(r'\bcell\s*\(\s*([^\s()]+)\s*\)\s*\{', text))
        areas = {}
        for i, match in enumerate(starts):
            block = text[match.end():starts[i+1].start() if i+1 < len(starts) else len(text)]
            area = re.search(r'\barea\s*:\s*([\d.eE+-]+)\s*;', block)
            if area:
                areas[match.group(1).strip('"')] = float(area.group(1))
        net = json.loads((a.out/'mapped.json').read_text())
        cells = net['modules']['wide_block']['cells']
        hist = {}
        for cell in cells.values():
            t = cell['type']; hist[t] = hist.get(t, 0)+1
        if {t: n for t, n in hist.items() if t not in areas} != {'ram128': 1, 'lut32': 1}:
            raise ValueError('unmapped logic or missing/duplicated memory blackboxes')
        m['mapped_cells'] = {t: n for t, n in hist.items() if t in areas}
        m['blackbox_instances'] = {'ram128': 1, 'lut32': 1}
        m['logic_cells'] = sum(m['mapped_cells'].values())
        m['logic_area_um2'] = sum(areas[t]*n for t, n in m['mapped_cells'].items())
        m['cell_area_um2'] = {t: areas[t] for t in m['mapped_cells']}
        m['status'] = 'PASS_LOGIC_ONLY_REFERENCE_LIBRARY_MAPPING'
    except Exception as e:
        m['error'] = {'type': type(e).__name__, 'message': str(e), 'traceback': traceback.format_exc()}
        raise
    finally:
        m['elapsed_seconds'] = time.monotonic()-started
        m['artifacts'] = [{'path': q.name, 'bytes': q.stat().st_size, 'sha256': sha(q)}
                          for q in sorted(a.out.iterdir()) if q.is_file() and q.name != 'manifest.json']
        put(a.out/'manifest.json', m)
    print(json.dumps({k: m[k] for k in ('status', 'mode', 'logic_cells', 'logic_area_um2')}))


if __name__ == '__main__':
    main()
