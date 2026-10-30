"""Allocated native 12-layer capability probe; immutable original technology."""
from pathlib import Path
import csv, datetime, json, os, re, subprocess, sys
from run_exports import ROOT, IMAGE, BIN, sha
from extend_upper_tech import extend
from check_access import check

DRIVER = Path(__file__).resolve().parent
revision = sys.argv[1]
out = ROOT/'upper_layer_probe'/revision
out.mkdir(parents=True, exist_ok=False)
common = ['singularity', 'exec', '--cleanenv', '--bind', str(ROOT/'tmp')+':/tmp', '--home', str(ROOT/'home'), '--pwd', str(out)]
platform = '/OpenROAD-flow-scripts/flow/platforms/nangate45/'
for source, name in [('lef/NangateOpenCellLibrary.tech.lef', 'original.tech.lef'), ('setRC.tcl', 'original.setRC.tcl')]:
    with (out/name).open('xb') as f:
        subprocess.run(common+[IMAGE, 'cat', platform+source], stdout=f, check=True)
extend(out/'original.tech.lef', out/'original.setRC.tcl', out/'model')
(out/'toy.v').write_text('module upper_probe(input a,b, output y,z); assign y=a; assign z=b; endmodule\n')
env = 'PINXY_TECH={},PINXY_RC={},PINXY_VERILOG={},PINXY_OUT={},PINXY_DRIVER={},PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT={}'.format(
    out/'model/research12.tech.lef', out/'model/research12.setRC.tcl', out/'toy.v', out, DRIVER, out/'access.tsv')
command = common+['--env', env, IMAGE, BIN, '-threads', '2', '-no_init', '-exit', str(DRIVER/'upper_probe.tcl')]
with (out/'native.log').open('x') as f:
    result = subprocess.run(command, stdout=f, stderr=subprocess.STDOUT)
record = {'scope': 'NATIVE_RESEARCH_UPPER_LAYER_TOY_PROBE_ONLY; not six-block, common-base, full rule or STA qualification',
          'native_returncode': result.returncode, 'scheduler_job': os.environ['SLURM_JOB_ID'],
          'driver_commit': (DRIVER/'driver_commit.txt').read_text().strip(), 'command': command,
          'completed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'system_qualified': False}
if (out/'access.tsv').exists():
    access = check(out/'access.tsv', True)
    (out/'access.json').write_text(json.dumps(access, indent=2)+'\n')
    record['actual_all_net_geometry'] = access
    with (out/'access.tsv').open() as f:
        rows = list(csv.DictReader(f, delimiter='\t'))
    record['actual_conductor_layers'] = sorted({r['layer'] for r in rows if r['kind'] != 'BTERM'})
    record['upper_layers_actually_used'] = all(l in record['actual_conductor_layers'] for l in ['metal11', 'metal12'])
    # Adaptive via10 bottom metal may overlap an existing fixed M10 pin only.
    lower = [r for r in rows if r['kind'] != 'BTERM' and r['layer'].startswith('metal') and int(r['layer'][5:]) <= 10]
    pins = [r for r in rows if r['kind'] == 'BTERM']
    contained = []
    for r in lower:
        contained.append(any(p['net'] == r['net'] and p['layer'] == r['layer']
                             and all(int(r[k]) >= int(p[k]) for k in ['x0', 'y0'])
                             and all(int(r[k]) <= int(p[k]) for k in ['x1', 'y1']) for p in pins))
    record['all_added_lower_metal_covered_by_original_M10_pin'] = all(contained)
report = out/'native.drc'
record['native_DRC_count'] = len(re.findall(r'^violation type:', report.read_text(), re.M)) if result.returncode == 0 and report.exists() else None
record['files'] = {p.name: {'sha256': sha(p), 'bytes': p.stat().st_size} for p in out.iterdir() if p.is_file()}
record['status'] = 'TOY_ROUTE_GATES_PASSED_NOT_SYSTEM_QUALIFIED' if (result.returncode == 0 and record.get('native_DRC_count') == 0
                   and record.get('actual_all_net_geometry', {}).get('pass') and record.get('upper_layers_actually_used')
                   and record.get('all_added_lower_metal_covered_by_original_M10_pin')) else 'NATIVE_TOY_PROBE_FAILED_OR_INCOMPLETE'
(out/'execution.json').write_text(json.dumps(record, indent=2)+'\n')
print('UPPER_PROBE_RESULT', record['status'], flush=True)
sys.exit(0 if record['status'] == 'TOY_ROUTE_GATES_PASSED_NOT_SYSTEM_QUALIFIED' else 1)
