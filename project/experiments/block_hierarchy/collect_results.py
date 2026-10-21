"""Read lightweight metadata for Issue #7 attempts; never run physical tools.

Run from the checkout after submitting or completing jobs. Detailed databases and
logs remain at their recorded remote paths. This collector does not hash large
databases on the login node: it reads hashes produced by the compute-node jobs.
"""
from datetime import datetime, timedelta, timezone
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import re

HERE = Path(__file__).resolve().parent
ATTEMPTS = {
    "vec-screen-01": 89441,
    "vec-screen-02": 89442,
    "vec-harden-01": 89443,
    "vec-top-01": 89444,
    "vec-top-02": 89445,
}
HOST = "yuzelu@10.129.166.172"
REMOTE = "/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7"
COLLECTOR = r'''
from pathlib import Path
import json, subprocess, re
root = Path(__ROOT__)
attempts = __ATTEMPTS__
sacct = subprocess.check_output([
    'sacct', '-j', ','.join(str(v) for v in attempts.values()),
    '--format=JobIDRaw,State,ExitCode,Elapsed,AllocCPUS,NodeList,Timelimit', '--parsable2', '--noheader'
], universal_newlines=True)
states = {}
for line in sacct.splitlines():
    values = line.split('|')
    if len(values) >= 7 and values[0].isdigit():
        states[int(values[0])] = dict(zip(('job_id','state','exit_code','elapsed','allocated_cpus','node','effective_time_limit'), values[:7]))
out = []
for name, job in attempts.items():
    path = root / name
    item = {'attempt': name, 'remote_path': str(path), 'job_id': job, 'sacct': states.get(job, {})}
    for filename in (
        'submission.json', 'port-validation.json', 'harness-contract.json', 'physical-interface-validation.json', 'resume-validation.json',
        'exit-code.txt', 'host.txt', 'started-utc.txt', 'finished-utc.txt',
        'image.sha256', 'tools.sha256', 'openroad-version.txt', 'yosys-version.txt',
        'orfs-commit.txt', 'runner-inputs.sha256', 'config-inputs.sha256',
        'abstract-source.txt', 'block-abstract-inputs.sha256', 'top-physical-inspection.txt',
        'resume-parent.txt', 'resume-parent-state.txt', 'resume-parent-inputs.sha256', 'resume-dry-run-target.txt',
    ):
        target = path / filename
        if target.is_file():
            text = target.read_text(errors='replace')
            item[filename] = json.loads(text) if filename.endswith('.json') else text.strip()
    metrics = {}
    for nickname in ('llhd_vec_original', 'llhd_vec_harness'):
        base = path / 'flow/logs/nangate45' / nickname / 'base'
        for filename in ('1_synth.json', '2_1_floorplan.json', '3_3_place_gp.json', '4_1_cts.json', '5_1_grt.json', '5_2_route.json', '6_report.json'):
            target = base / filename
            if target.is_file():
                metrics[str(target)] = json.loads(target.read_text())
    item['flow_metrics'] = metrics
    equivalence = {}
    for nickname in ('llhd_vec_original', 'llhd_vec_harness'):
        base = path / 'flow/logs/nangate45' / nickname / 'base'
        for stem in ('4_rsz_lec', '6_final_lec'):
            logs = [base / (stem + suffix) for suffix in ('_check.log', '.log')]
            present = [target for target in logs if target.is_file()]
            if present:
                content = '\n'.join(target.read_text(errors='replace') for target in present).lower()
                status = 'identical' if 'circuits are identical' in content else 'different' if 'circuits are different' in content else 'started_no_result'
                equivalence[nickname + '/' + stem] = {'status': status, 'logs': [str(target) for target in present], 'scope': 'stage gate-level comparison, not original RTL to physical equivalence'}
    item['stage_equivalence_checks'] = equivalence
    io_models = {}
    for nickname in ('llhd_vec_original', 'llhd_vec_harness'):
        for stem in ('1_synth', '2_floorplan', '6_final'):
            target = path / 'flow/results/nangate45' / nickname / 'base' / (stem + '.sdc')
            if target.is_file():
                lines = [line for line in target.read_text(errors='replace').splitlines() if re.search(r'\b(set_load|set_driving_cell|set_input_transition)\b', line)]
                io_models[str(target)] = {'explicit_model_line_count': len(lines), 'first_lines': lines[:20]}
    item['exported_sdc_external_io_models'] = io_models
    item['logs'] = {
        'slurm': str(path / f'slurm-{job}.log'),
        'elaboration': str(path / 'vec-elab.log'),
        'flow': str(path / 'flow.log'),
        'resume_dry_run': str(path / 'resume-dry-run.txt') if (path / 'resume-dry-run.txt').exists() else None,
    }
    item['output_hash_index'] = str(path / 'result-files.sha256') if (path / 'result-files.sha256').exists() else None
    products = {}
    for nickname in ('llhd_vec_original', 'llhd_vec_harness'):
        base = path / 'flow/results/nangate45' / nickname / 'base'
        products[nickname] = {name: str(base / name) for name in (
            '6_final.odb', '6_final.v', '6_final.sdc', '6_final.spef', '6_final.gds',
            'vec_engine.lef', 'vec_engine_typ.lib',
        ) if (base / name).is_file()}
    item['existing_products_not_standalone_validation'] = products
    interface = item.get('physical-interface-validation.json', {})
    pin_check = item.get('port-validation.json', {})
    item['validation_summary'] = {
        'sacct_completed_is_only_execution_status': item['sacct'].get('state') == 'COMPLETED',
        'abstract_signal_names_and_directions_pass': pin_check.get('pass'),
        'physical_signal_interface_pass': interface.get('all_expected_signal_pins_present_connected_and_direction_correct'),
        'extra_physical_signal_pins_require_review': {scope: interface.get(scope, {}).get('extra_signal_pins') for scope in ('top', 'macro')},
        'timing_reports_present': {name: (path / name).is_file() for name in ('top-check-setup.rpt', 'top-clocks.rpt', 'top-paths.rpt', 'top-electrical.rpt')},
        'acceptance_note': 'COMPLETED never overrides failed/missing interface checks, electrical violations or missing timing coverage. No formal/system signoff.',
    }
    out.append(item)
print(json.dumps({'attempts': out, 'sacct_raw': sacct}, indent=2))
'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", action="append", default=[], metavar="NAME:JOB_ID", help="Add a submitted attempt; repeat for multiple jobs. Historical Issue #7 attempts are always included.")
    parser.add_argument("--runner-commit", help="Repository snapshot recorded after submission; per-attempt submitted hashes remain authoritative")
    args = parser.parse_args()
    attempts = dict(ATTEMPTS)
    if args.runner_commit and not re.fullmatch(r"[0-9a-fA-F]{40}", args.runner_commit):
        parser.error("--runner-commit must be a complete 40-character commit SHA")
    output = HERE / "results/issue-7.json"
    previous = json.loads(output.read_text(encoding="utf-8")) if output.exists() else {}
    runner_commit = args.runner_commit or previous.get("runner_commit")
    for item in previous.get("attempts", []):
        name, job = item.get("attempt"), item.get("job_id")
        if isinstance(name, str) and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", name) and str(job).isdigit() and int(job) > 0:
            if name in attempts and attempts[name] != int(job):
                parser.error("previous index conflicts with the immutable attempt/job mapping: " + name)
            attempts[name] = int(job)
    for value in args.attempt:
        match = re.fullmatch(r"([a-z0-9][a-z0-9-]{0,63}):([0-9]+)", value)
        if not match:
            parser.error("--attempt must use NAME:JOB_ID with a safe lowercase attempt name")
        attempts[match.group(1)] = int(match.group(2))
    source = COLLECTOR.replace("__ROOT__", repr(REMOTE)).replace("__ATTEMPTS__", repr(attempts))
    collected = json.loads(subprocess.check_output(
        ["ssh", "-o", "BatchMode=yes", HOST, "python3 -c " + shlex.quote(source)],
        text=True, encoding="utf-8",
    ))
    remaining = [
        "Inspect exported Liberty timing coverage and final route electrical/timing violations before accepting the pilot.",
        "Scale integration harness to useful multiple-Block connectivity and then fixed/restricted layers.",
    ]
    active = [a['attempt'] for a in collected['attempts'] if a['sacct'].get('state') in ('RUNNING', 'PENDING', 'COMPLETING')]
    if active:
        remaining.insert(0, 'Await terminal job state: ' + ', '.join(active))
    result = {
        "schema_version": 1,
        "issue": "https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7",
        "updated_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "source_commit": "f7db8a22791a1ce9dc13e7c90b0b9b9386169aa5",
        "source_scope": "Original full-width llaccel v1 vec_engine and a direct one-macro integration harness",
        "runner_commit": runner_commit,
        "runner_commit_note": "This is a repository code snapshot recorded after job submission, not a claim that the jobs started from a committed checkout. Exact submitted versions and historical differences are bound by each remote runner-inputs.sha256; the base repository commit is not the experiment runner version.",
        "claims": {
            "complete_llaccel_core": False,
            "prefabricated_base": False,
            "restricted_metal_customization": False,
            "system_sta_signoff": False,
            "source_rtl_to_physical_formal_equivalence_performed": False,
        },
        "timing_assumption": "3 ns single-clock Nangate45 typical corner; 0.6 ns top IO budget. Block and top budgets are not added to claim a system period.",
        "scheduler_policy": "Current runner requests --time=0 and verifies scontrol TimeLimit=UNLIMITED. User removed artificial runtime limits; historical timed attempts retain their actual sacct limits and terminal states.",
        "remaining": remaining,
        **collected,
    }
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
