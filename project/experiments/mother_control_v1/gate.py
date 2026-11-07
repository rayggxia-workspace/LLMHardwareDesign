"""Replay the unchanged public-port regression on the actual final mother netlist."""
import argparse, hashlib, json, os, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--upstream', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    final = args.candidate.resolve() / 'flow/results/nangate45/mother_control_64/base/6_final.v'
    original_sha = digest(final)
    liberty = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    cells = out / 'cells.sv'
    command = ['yosys', '-Q', '-p', 'read_liberty -ignore_miss_func -ignore_miss_dir ' + str(liberty) + '; write_verilog -noattr ' + str(cells)]
    with (out / 'cells.log').open('w') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    subprocess.run([sys.executable, '-B', str(HERE / 'regression.py'), '--out', str(out / 'replay'),
                    '--upstream', str(args.upstream), '--netlist', str(final), '--cells', str(cells)], check=True)
    replay = json.loads((out / 'replay/result.json').read_text())
    assert replay['passed'] and replay['physical_netlist'] and len(replay['results']) == 54
    assert digest(final) == original_sha
    (out / 'result.json').write_text(json.dumps(dict(schema='mother-final-netlist/1', passed=True,
        final_netlist_sha256=original_sha, liberty_sha256=digest(liberty), cells_sha256=digest(cells),
        regression_sha256=digest(out / 'replay/result.json'), runs=54, sdf_annotated=False,
        scope='functional final netlist with actual SRAM; extracted STA is a separate acceptance gate'), indent=2) + '\n')

if __name__ == '__main__':
    main()
