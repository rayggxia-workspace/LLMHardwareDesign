"""Map the exact tested complete native M; area evidence, not final P&R."""
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
from reference_source.native import check as native_check

ROOT = Path(__file__).resolve().parents[3]
LIB = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
FILES = ['m_native_s32.sv', 'weight_records.sv', 'm_group_s32.sv', 'projection_context_s32.sv', 'scale_group_s32.sv']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--rtl-run', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--leaf', action='store_true')
    a = p.parse_args()
    assert len(os.sched_getaffinity(0)) in (10, 12)
    anchors = native_check()
    top = 'm_native_leaf_s32' if a.leaf else 'm_native_s32'
    files = FILES + (['m_native_leaf_s32.sv'] if a.leaf else [])
    sources = {f'project/rtl/w8a16_v1/{name}': sha(ROOT / 'project/rtl/w8a16_v1' / name) for name in files}
    for name, digest in sources.items():
        assert sha(a.rtl_run / 'source' / name) == digest, ('not the exact tested RTL', name)
    for seed in range(25011, 25017):
        result = json.loads((a.rtl_run / f"{'leaf' if a.leaf else 'native'}-seed-{seed}/result.json").read_text())
        assert result['passed'] and len(result['runs']) == 3
        for row in result['runs']:
            assert row['receipt'].startswith('PASS leaf ' if a.leaf else 'PASS native ')
    a.out.mkdir(parents=True, exist_ok=False)
    wrapper = Path(__file__).parent / 'reference_source/abc_batch.py'
    wrapper.chmod(0o755)
    script = f'read_liberty -lib {LIB}\n'
    script += 'read_verilog -sv ' + ' '.join(str(ROOT / name) for name in sources) + '\n'
    script += f'hierarchy -check -top {top}\nproc\nopt\nwrite_json operators.json\nsynth -top {top} -noabc\n'
    script += f'dfflibmap -liberty {LIB}\nabc -exe {wrapper} -liberty {LIB}\nclean\ncheck -assert\n'
    # Real tie cells are required before the pre-mapped netlist reaches
    # OpenROAD. Bare 1'b0/1'b1 links otherwise become non-special POWER/GROUND
    # one_/zero_ nets feeding logic, which TritonRoute correctly refuses.
    # Count both cells; native repair_tie_fanout subsequently places/replicates
    # them. Do not relabel logic nets as PG or skip connectivity verification.
    script += f'flatten -noscopeinfo\nclean\nhilomap -hicell LOGIC1_X1 Z -locell LOGIC0_X1 Z\nclean\ncheck -assert\nstat -liberty {LIB}\nwrite_verilog -noattr mapped.v\nwrite_json mapped.json\n'
    (a.out / 'map.ys').write_text(script)
    result = dict(passed=False, physical_qualified=False, top=top, source_SHA256=sources, source_sha256=sources, mapped=False, liberty_sha256=sha(LIB),
                  anchors=anchors, start_unix=time.time(), affinity=sorted(os.sched_getaffinity(0)),
                  W_register_bytes=4608, RF_register_bytes=512, scale_FIFO_bytes=64,
                  scope='actual product M aperture including all active scope/record/frame logic' if a.leaf else 'complete logical native M unit; not the product endpoint wrapper')
    try:
        with (a.out / 'map.log').open('w') as output:
            proc = subprocess.run(['yosys', '-s', str(a.out / 'map.ys')], cwd=a.out,
                                  env=dict(os.environ, ISSUE250_ABC_TRANSPORT_DIR=str(a.out)),
                                  stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT)
        assert proc.returncode == 0
        module = json.loads((a.out / 'mapped.json').read_text())['modules'][top]
        cells = collections.Counter(cell['type'] for cell in module['cells'].values())
        assert not any(name.startswith('$') for name in cells)
        text = LIB.read_text()
        matches = list(re.finditer(r'\bcell\s*\(\s*([^\s)]+)\s*\)\s*\{', text))
        areas = {}
        for index, match in enumerate(matches):
            body = text[match.end():matches[index + 1].start() if index + 1 < len(matches) else len(text)]
            areas[match.group(1)] = float(re.search(r'\barea\s*:\s*([\d.eE+-]+)\s*;', body).group(1))
        result.update(passed=True, mapped=True, area_um2=sum(areas[name] * count for name, count in cells.items()),
                      cells=dict(cells), ports={name:dict(direction=row['direction'],bits=len(row['bits'])) for name,row in module['ports'].items()},
                      mapped_SHA256={name:sha(a.out / name) for name in ['mapped.json', 'mapped.v']})
        result.update(mapped_area_um2=result['area_um2'], cell_counts=dict(cells), reused_artifacts=dict(scope='same-run fresh mapping', artifacts={str(a.out / name):sha(a.out / name) for name in ['mapped.json','mapped.v']}))
        assert json.loads((a.out/'abc-liberty-conversion.json').read_text())['passed']
        assert json.loads((a.out/'abc-mapping.json').read_text())['passed']
        print(json.dumps(dict(passed=True, top=top, area_um2=result['area_um2'], port_bits=sum(row['bits'] for row in result['ports'].values()))))
    finally:
        result['end_unix'] = time.time()
        (a.out / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
