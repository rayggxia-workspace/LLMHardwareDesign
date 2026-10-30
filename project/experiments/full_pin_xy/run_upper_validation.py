"""Independent process readback of the already-routed upper-layer toy.

This checks tool access/geometry only. It is not an openTPU/llaccel function,
frozen common base, calibrated extraction, complete DRC, or STA qualification.
"""
from pathlib import Path
import csv, datetime, json, os, re, subprocess, sys
from run_exports import ROOT, IMAGE, BIN, sha
from check_access import check
from run_parent_trial import tcl

DRIVER = Path(__file__).resolve().parent
source_revision, revision = sys.argv[1:3]
source = ROOT/'upper_layer_probe'/source_revision
previous = json.loads((source/'execution.json').read_text())
assert previous['status'] == 'TOY_ROUTE_GATES_PASSED_NOT_SYSTEM_QUALIFIED'
odb = source/'routed.odb'
before = sha(odb)
out = ROOT/'upper_layer_validation'/revision
out.mkdir(parents=True, exist_ok=False)
script = out/'validate.tcl'
script.write_text('\n'.join([
    'read_db '+tcl(odb),
    'set_routing_layers -signal metal11-metal12 -clock metal11-metal12',
    'drt::check_drc -output_file '+tcl(out/'independent.drc'),
    'source '+tcl(DRIVER/'export_access.tcl'),
    'help repair_timing', 'help repair_design', 'help detailed_placement', 'help remove_fillers',
    'puts "INDEPENDENT_UPPER_TOY_READBACK_EXECUTED"'])+'\n')
env = 'PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'access.tsv')
command = ['singularity', 'exec', '--cleanenv', '--bind', str(ROOT/'tmp')+':/tmp', '--home', str(ROOT/'home'), '--pwd', str(out),
           '--env', env, IMAGE, BIN, '-threads', '1', '-no_init', '-exit', str(script)]
with (out/'native.log').open('x') as f:
    result = subprocess.run(command, stdout=f, stderr=subprocess.STDOUT)
report = out/'independent.drc'
count = len(re.findall(r'^violation type:', report.read_text(), re.M)) if result.returncode == 0 and report.exists() else None
access = check(out/'access.tsv', True) if (out/'access.tsv').exists() else None
identical = (out/'access.tsv').exists() and sha(out/'access.tsv') == sha(source/'access.tsv')
rec = {'scope': 'INDEPENDENT_RESEARCH_UPPER_TOY_GEOMETRY_ONLY_NOT_FULL_SYSTEM_QUALIFICATION',
       'source_probe': str(source/'execution.json'), 'source_probe_SHA': sha(source/'execution.json'),
       'source_odb_SHA': before, 'source_unchanged': before == sha(odb), 'fresh_process': True,
       'native_returncode': result.returncode, 'native_DRC_count': count, 'whole_geometry': access,
       'exact_geometry_export_equal_to_original': identical, 'full_qualification': False,
       'driver_commit': (DRIVER/'driver_commit.txt').read_text().strip(), 'scheduler_job': os.environ['SLURM_JOB_ID'],
       'completed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'files': {p.name: {'sha256': sha(p), 'bytes': p.stat().st_size} for p in out.iterdir() if p.is_file()}}
rec['status'] = 'INDEPENDENT_TOY_ACCESS_PASSED_NOT_SYSTEM_QUALIFIED' if count == 0 and access and access['pass'] and identical and rec['source_unchanged'] else 'INDEPENDENT_TOY_CHECK_FAILED'
(out/'execution.json').write_text(json.dumps(rec, indent=2)+'\n')
print('UPPER_INDEPENDENT_VALIDATION', rec['status'], flush=True)
sys.exit(0 if rec['status'] == 'INDEPENDENT_TOY_ACCESS_PASSED_NOT_SYSTEM_QUALIFIED' else 1)
