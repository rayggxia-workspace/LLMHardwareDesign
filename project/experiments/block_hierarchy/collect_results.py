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
import calendar, json, subprocess, re, time

def file_origin(target, attempt, parent, started_epoch):
    if not target.is_file():
        return {'origin': 'unknown', 'reason': 'absent'}
    info = target.stat()
    result = {'origin': 'unknown', 'size_bytes': info.st_size, 'mtime_ns': info.st_mtime_ns}
    if parent is not None:
        inherited = parent / target.relative_to(attempt)
        if inherited.is_file():
            old = inherited.stat()
            if (old.st_size, old.st_mtime_ns) == (info.st_size, info.st_mtime_ns):
                if info.st_size <= 1024 * 1024 and inherited.read_bytes() != target.read_bytes():
                    result['reason'] = 'copy_metadata_matches_but_small_file_content_differs'
                    return result
                result.update(origin='inherited', reason='parent_copy_size_mtime_match' + ('_and_content_match' if info.st_size <= 1024 * 1024 else ''), parent_path=str(inherited))
                return result
    if started_epoch is not None and info.st_mtime >= started_epoch + 1:
        result.update(origin='current', reason='modified_after_job_start_second')
    else:
        result['reason'] = 'missing_start_time_or_preexisting_or_same_second_ambiguous'
    return result

def combined_lec_status(statuses):
    statuses = set(statuses)
    if 'conflicting_results' in statuses or {'identical', 'different'} <= statuses:
        return 'conflicting_results'
    if 'different' in statuses:
        return 'different'
    if 'identical' in statuses:
        return 'identical'
    return 'started_no_result' if statuses else None

def summarize_lec(entries, skipped):
    current = combined_lec_status(e['result'] for e in entries if e['provenance']['origin'] == 'current')
    inherited = combined_lec_status(e['result'] for e in entries if e['provenance']['origin'] == 'inherited')
    unknown = combined_lec_status(e['result'] for e in entries if e['provenance']['origin'] == 'unknown')
    status = current or ('inherited_log_only_not_executed' if inherited else 'unknown_origin')
    if skipped and current is not None:
        status = 'unexpected_current_logs_despite_skip_policy'
    elif skipped:
        status = 'inherited_log_only_not_executed' if inherited else 'not_executed_no_current_evidence'
    elif current == 'identical' and unknown in ('different', 'conflicting_results'):
        status = 'conflicting_or_ambiguous_results'
    return {
        'status': status, 'current_attempt_status': current,
        'inherited_parent_status': inherited, 'unknown_origin_status': unknown,
        'cross_generation_results_disagree': bool(current in ('identical', 'different') and inherited in ('identical', 'different') and current != inherited),
        'logs': entries,
        'scope': 'Per-log lineage; only current-attempt logs describe this attempt. Gate-level phase comparison, not original RTL-to-physical equivalence.',
    }

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
    if item['sacct'].get('state') == 'RUNNING':
        try:
            item['live_resource_snapshot'] = subprocess.check_output([
                'sstat', '-j', str(job) + '.batch', '--noheader', '--parsable2',
                '--format=JobID,AveCPU,MaxRSS'
            ], universal_newlines=True).strip()
        except (OSError, subprocess.CalledProcessError) as error:
            item['live_resource_snapshot_error'] = str(error)
    for filename in (
        'submission.json', 'port-validation.json', 'harness-contract.json', 'physical-interface-validation.json', 'resume-validation.json', 'regression-result.json', 'macro-view-validation.json', 'pdn-connectivity.json', 'post-pdn-connectivity.json', 'pdn-source-via-reports.json', 'pg-access-selection.json',
        'launch-code-snapshot.json',
        'exit-code.txt', 'host.txt', 'started-utc.txt', 'finished-utc.txt',
        'output-hash-exit-code.txt',
        'image.sha256', 'tools.sha256', 'openroad-version.txt', 'yosys-version.txt',
        'orfs-commit.txt', 'runner-inputs.sha256', 'config-inputs.sha256',
        'abstract-source.txt', 'block-abstract-inputs.sha256', 'top-physical-inspection.txt',
        'resume-parent.txt', 'resume-parent-state.txt', 'resume-parent-inputs.sha256', 'resume-dry-run-target.txt',
        'verilator-version.txt', 'regression-tools.sha256', 'regression-cxx-version.txt', 'regression-source.sha256',
        'phase-lec-policy.txt',
        'compat-patch.diff', 'compat-inputs.sha256',
        'pdn-audit-inputs.sha256', 'pg-access-obstructions.tsv', 'pg-access-pins.tsv', 'pg-removed-sites.tsv', 'pg-retained-landings.tsv', 'pdn-macro-pg-iterms.tsv', 'post-pdn-macro-pg-iterms.tsv',
    ):
        target = path / filename
        if target.is_file():
            if target.suffix == '.tsv':
                manifest = path / 'result-files.sha256'
                digest = None
                if manifest.is_file():
                    for line in manifest.read_text().splitlines():
                        parts = line.split(None, 1)
                        if len(parts) == 2 and parts[1].lstrip('*') == str(target):
                            digest = parts[0]
                            break
                item[filename] = {'path': str(target), 'size_bytes': target.stat().st_size,
                                  'sha256_from_compute_manifest': digest,
                                  'hash_status': 'recorded' if digest else 'missing_or_not_yet_recorded',
                                  'hash_manifest': str(manifest), 'content_included': False}
            else:
                text = target.read_text(errors='replace')
                item[filename] = json.loads(text) if filename.endswith('.json') else text.strip()
    submitted = item.get('submission.json', {})
    parent = Path(submitted['resume_from']) if submitted.get('mode') == 'resume' and submitted.get('resume_from') else None
    if parent is not None and parent.parent != root:
        parent = None
    try:
        started_epoch = calendar.timegm(time.strptime(item.get('started-utc.txt', ''), '%Y-%m-%dT%H:%M:%SZ'))
    except ValueError:
        started_epoch = None
    item['verification_policy'] = {
        'skip_phase_lec': submitted.get('skip_phase_lec', False),
        'proof_inheritance_claimed': False,
    }
    if submitted.get('block_attempt'):
        block_path = Path(submitted['block_attempt'])
        block_receipt = block_path / 'submission.json'
        if block_path.parent == root and block_receipt.is_file():
            block_submission = json.loads(block_receipt.read_text())
            item['verification_policy']['block_implementation_skip_phase_lec'] = block_submission.get('skip_phase_lec', False)
    metrics = {}
    for nickname in ('llhd_vec_original', 'llhd_vec_harness'):
        base = path / 'flow/logs/nangate45' / nickname / 'base'
        for filename in ('1_synth.json', '2_1_floorplan.json', '3_3_place_gp.json', '4_1_cts.json', '5_1_grt.json', '5_2_route.json', '6_report.json'):
            target = base / filename
            if target.is_file():
                metrics[str(target)] = json.loads(target.read_text())
    item['flow_metrics'] = metrics
    stage_artifacts = {}
    for nickname in ('llhd_vec_original', 'llhd_vec_harness'):
        logs = path / 'flow/logs/nangate45' / nickname / 'base'
        results = path / 'flow/results/nangate45' / nickname / 'base'
        if logs.is_dir() or results.is_dir():
            entries = {}
            for label, checkpoint, metric in (
                ('cts', '4_cts.odb', '4_1_cts.json'),
                ('global_route', '5_1_grt.odb', '5_1_grt.json'),
                ('detailed_route', '5_2_route.odb', '5_2_route.json'),
                ('final_report', '6_final.odb', '6_report.json'),
            ):
                checkpoint_origin = file_origin(results / checkpoint, path, parent, started_epoch)
                metrics_origin = file_origin(logs / metric, path, parent, started_epoch)
                origins = {checkpoint_origin['origin'], metrics_origin['origin']}
                aggregate_origin = next(iter(origins)) if len(origins) == 1 else 'mixed' if origins == {'current', 'inherited'} else 'unknown'
                present = (results / checkpoint).is_file() and (logs / metric).is_file()
                entries[label] = {
                    'checkpoint': str(results / checkpoint),
                    'metrics': str(logs / metric),
                    'checkpoint_and_metrics_present': present,
                    'checkpoint_provenance': checkpoint_origin,
                    'metrics_provenance': metrics_origin,
                    'origin': aggregate_origin,
                    'current_attempt_completion_artifacts': present and aggregate_origin == 'current',
                }
            stage_artifacts[nickname] = {
                'stages': entries,
                'temporary_logs_present': [str(t) for t in sorted(logs.glob('*.tmp.log'))],
                'note': 'Stage completion requires its output checkpoint and closing metrics, not a DRT/RSZ progress message. Resume may inherit completed stages; see resume-validation.json. Existence does not imply timing/DRC acceptance.',
            }
    item['physical_stage_artifacts'] = stage_artifacts
    equivalence = {}
    for nickname in ('llhd_vec_original', 'llhd_vec_harness'):
        base = path / 'flow/logs/nangate45' / nickname / 'base'
        for stem in ('4_rsz_lec', '6_final_lec'):
            logs = [base / (stem + suffix) for suffix in ('_check.log', '.log')]
            present = [target for target in logs if target.is_file()]
            if present:
                entries = []
                for target in present:
                    content = target.read_text(errors='replace').lower()
                    flags = [status for status, marker in (('identical', 'circuits are identical'), ('different', 'circuits are different')) if marker in content]
                    entries.append({'path': str(target), 'result': combined_lec_status(flags) or 'started_no_result', 'provenance': file_origin(target, path, parent, started_epoch)})
                skipped = item.get('submission.json', {}).get('skip_phase_lec', False)
                equivalence[nickname + '/' + stem] = summarize_lec(entries, skipped)
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
        'regression': str(path / 'regression.log') if (path / 'regression.log').exists() else None,
        'resume_dry_run': str(path / 'resume-dry-run.txt') if (path / 'resume-dry-run.txt').exists() else None,
        'post_submission_read_only_grt_policy_observation': str(path / 'grt-repair-policy-observation.txt') if (path / 'grt-repair-policy-observation.txt').exists() else None,
        'post_submission_read_only_repair_timing_help': str(path / 'repair-timing-help.txt') if (path / 'repair-timing-help.txt').exists() else None,
        'post_submission_read_only_psm_policy_observation': str(path / 'psm-policy-observation.txt') if (path / 'psm-policy-observation.txt').exists() else None,
        'abstract': str(path / 'abstract.log') if (path / 'abstract.log').exists() else None,
        'pdn_audit': str(path / 'pdn-audit.log') if (path / 'pdn-audit.log').exists() else None,
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
    item['new_macro_view_products'] = {name: str(path / 'macro-view' / name) for name in ('vec_engine.lef', 'vec_engine_typ.lib') if (path / 'macro-view' / name).is_file()}
    interface = item.get('physical-interface-validation.json', {})
    pin_check = item.get('port-validation.json', {})
    item['validation_summary'] = {
        'sacct_completed_is_only_execution_status': item['sacct'].get('state') == 'COMPLETED',
        'abstract_signal_names_and_directions_pass': pin_check.get('pass'),
        'physical_signal_interface_pass': interface.get('all_expected_signal_pins_present_connected_and_direction_correct'),
        'explicit_pdn_connectivity': item.get('pdn-connectivity.json'),
        'pg_access_site_selection_or_check': item.get('pg-access-selection.json'),
        'early_guarded_pdn_connectivity': item.get('post-pdn-connectivity.json'),
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
        name, job = match.group(1), int(match.group(2))
        if job <= 0 or (name in attempts and attempts[name] != job):
            parser.error("attempt/job mapping must be positive and immutable: " + name)
        attempts[name] = job
    source = COLLECTOR.replace("__ROOT__", repr(REMOTE)).replace("__ATTEMPTS__", repr(attempts))
    collected = json.loads(subprocess.check_output(
        ["ssh", "-o", "BatchMode=yes", HOST, "python3 -c " + shlex.quote(source)],
        text=True, encoding="utf-8",
    ))
    remaining = [
        "Close recorded block and parent 3ns setup violations and block max-cap violations; physical/PG/interface checks do not constitute timing or system signoff.",
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
        "source_scope": "Original full-width llaccel v1 vec_engine and its full math/vector regression with one recorded test-only unsigned-literal compatibility fix; direct one-macro integration harness",
        "runner_commit": runner_commit,
        "runner_commit_note": "Repository code snapshot for review. A per-attempt launch-code-snapshot.json, when present, records a verified clean committed launch; historical jobs submitted before their snapshot remain bound by remote runner-inputs.sha256/launcher_sha256 and are not retrospectively claimed to have launched from that commit.",
        "claims": {
            "complete_llaccel_core": False,
            "prefabricated_base": False,
            "restricted_metal_customization": False,
            "system_sta_signoff": False,
            "source_rtl_to_physical_formal_equivalence_performed": False,
        },
        "timing_assumption": "3 ns single-clock Nangate45 typical corner; 0.6 ns top IO budget. Block and top budgets are not added to claim a system period.",
        "scheduler_policy": "Current runner requests --time=0 and verifies scontrol TimeLimit=UNLIMITED. User removed artificial runtime limits; historical timed attempts retain their actual sacct limits and terminal states.",
        "diagnostic_evidence": {
            "pdn_disconnected_api_probe": REMOTE + "/pdn-api-diagnostic-01/",
            "pdn_via_landing_geometry_probe": REMOTE + "/pdn-geometry-diagnostic-01/",
            "actual_fixed_image_spacing_tables": REMOTE + "/pdn-spacing-evidence-01/",
            "mock_proc_source_scope_regression": REMOTE + "/pdn-hook-scope-diagnostic-01/",
            "obsolete_pending_top_cancellation": REMOTE + "/slurm-obsolete-89449-20261021/",
            "mock_proc_source_old_filter_negative_control": REMOTE + "/pdn-hook-scope-negative-01/",
            "active_jobs_name_update": REMOTE + "/slurm-name-update-20261021/",
            "scope": "Selected compute-node read-only/in-memory geometry and PG probes, plus a lightweight mocked Tcl scope regression. No original database rewrite or PI rerun. First geometry probe failed on an API name; probe-02.log is the successful via-shape observation. Mock scope checks are not EDA evidence. Metadata rename does not alter inputs or time limits.",
        },
        "remaining": remaining,
        **collected,
    }
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
