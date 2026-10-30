"""Replay exact existing leaf RC/constraints and expose real critical paths.

No new route, buffer, clock, constraint or library; inherited violations remain.
Native report completion is not a timing pass or a physical qualification.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import datetime, json, os, re, subprocess, sys, traceback
from run_exports import ROOT, IMAGE, BIN, sha
from run_parent_trial import BASE, C_REVISION, tcl

DRIVER = Path(__file__).resolve().parent


def one(case, variant, revision):
    physical, plan = (BASE[case], 'A') if variant == 'A' else (C_REVISION[case], 'C')
    clean = ROOT/'finalized'/physical/(case+'-'+plan)
    proof = json.loads((clean/'execution.json').read_text())
    assert proof['independent_DRC_count'] == 0 and proof['whole_access']['pass']
    source = Path(proof['legacy_RC_STA_receipt'])
    old = json.loads(source.read_text())
    odb, spef, sdc = clean/'clean.odb', source.parent/'extracted.spef', Path(old['source_sdc'])
    assert sha(odb) == proof['clean_odb_sha256']
    assert sha(spef) == old['outputs']['extracted.spef']['sha256']
    assert sha(sdc) == old['input_sha256'][str(sdc)]
    out = ROOT/'leaf_diagnosis'/revision/(case+'-'+variant)
    out.mkdir(parents=True, exist_ok=False)
    inputs = {str(p): sha(p) for p in [odb, spef, sdc, source, clean/'execution.json']}
    lines = ['read_liberty '+tcl(p) for p in old['libs']]
    lines += ['read_db '+tcl(odb), 'read_sdc '+tcl(sdc),
              'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl', 'read_spef '+tcl(spef),
              'report_units', 'report_worst_slack -max -digits 6 > '+tcl(out/'setup.txt'),
              'report_worst_slack -min -digits 6 > '+tcl(out/'hold.txt'),
              'report_checks -path_delay max -group_path_count 12 -endpoint_path_count 1 -fields {capacitance slew fanout} -format full_clock_expanded -digits 6 > '+tcl(out/'critical_setup.txt'),
              'report_checks -path_delay min -group_path_count 12 -endpoint_path_count 1 -fields {capacitance slew fanout} -format full_clock_expanded -digits 6 > '+tcl(out/'critical_hold.txt'),
              'report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > '+tcl(out/'checks.txt'),
              'check_setup -verbose > '+tcl(out/'constraint_coverage.txt'),
              'report_parasitic_annotation -report_unannotated > '+tcl(out/'parasitic_coverage.txt')]
    script = out/'diagnose.tcl'
    script.write_text('\n'.join(lines)+'\n')
    command = ['singularity', 'exec', '--cleanenv', '--bind', str(ROOT/'tmp')+':/tmp',
               '--bind', '/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
               '--bind', '/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
               '--home', str(ROOT/'home'), '--pwd', str(out), IMAGE, BIN, '-threads', '4', '-no_init', '-exit', str(script)]
    with (out/'native.log').open('x') as f:
        result = subprocess.run(command, stdout=f, stderr=subprocess.STDOUT)
    replay = {}
    for kind in ['setup', 'hold']:
        pattern = r'worst slack (?:max|min)\s+([-\d.]+)'
        a = re.search(pattern, (source.parent/('timing.'+kind+'.txt')).read_text())
        b = re.search(pattern, (out/(kind+'.txt')).read_text()) if (out/(kind+'.txt')).exists() else None
        replay[kind] = {'original_ns': float(a[1]) if a else None, 'replay_ns': float(b[1]) if b else None,
                        'delta_ns': float(b[1])-float(a[1]) if a and b else None}
    matched = all(q['delta_ns'] is not None and abs(q['delta_ns']) <= 1e-5 for q in replay.values())
    rec = {'scope': 'EXACT_EXISTING_RC_CONSTRAINT_CRITICAL_PATH_DIAGNOSIS_NOT_QUALIFICATION',
           'case': case, 'variant': variant, 'physical_revision': physical,
           'source_inputs_SHA': inputs, 'source_unchanged': all(sha(Path(p)) == h for p, h in inputs.items()),
           'native_returncode': result.returncode, 'worst_slack_replay': replay,
           'exact_worst_slack_reproduced': matched, 'full_qualification': False,
           'driver_commit': (DRIVER/'driver_commit.txt').read_text().strip(), 'scheduler_job': os.environ['SLURM_JOB_ID'],
           'completed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'files': {p.name: {'sha256': sha(p), 'bytes': p.stat().st_size} for p in out.iterdir() if p.is_file()}}
    (out/'execution.json').write_text(json.dumps(rec, indent=2)+'\n')
    print('LEAF_CRITICAL_DIAGNOSIS', case, variant, matched, flush=True)
    return result.returncode == 0 and matched and rec['source_unchanged']


def safe(args):
    try:
        return one(*args)
    except Exception:
        traceback.print_exc()
        return False


if __name__ == '__main__':
    assert int(os.environ['SLURM_CPUS_PER_TASK']) >= 8
    revision = sys.argv[1]
    tasks = [(c, v, revision) for c in ['vector', 'opentpu_aux', 'llaccel_aux'] for v in (['A'] if c == 'llaccel_aux' else ['A', 'C'])]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(safe, tasks))
    sys.exit(0 if all(results) else 1)
