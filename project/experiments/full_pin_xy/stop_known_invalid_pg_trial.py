"""Stop only our specifically identified NEW trial after a proven fixed-PG short.

No elapsed-time criterion, no unrelated job changes, no output deletion.
Run on the authorized server with a frozen proof copied under this task root.
"""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys
from run_exports import ROOT,sha

proof=Path(sys.argv[1]).resolve();assert ROOT.resolve() in proof.parents
r=json.loads(proof.read_text());assert r['case']=='llaccel_aux' and r['scheduler_job']=='92369'
assert r['direct_contact_pin_count']>0 and r['actual_PG_before_and_after_move_byte_identical'] and r['all_actual_moved_pins_match_complete_original_C']
trial=ROOT/'trials/full-other-r01/llaccel_aux-C';execution=json.loads((trial/'execution.json').read_text())
assert execution['scheduler_job']=='92369' and execution['source_sha256']==r['original_odb_sha256']
assert execution['driver_commit']=='f08e02609eaa47d4cad115b42e5df7e529dc6947'
assert execution['selected_pin_count']==13184
assert sha(trial/'moved.pins.tsv')==r['moved_pins_sha256']
assert sha(trial/'before.pdn.tsv')==sha(trial/'moved.pdn.tsv')==r['moved_PG_sha256']
info=subprocess.check_output(['scontrol','show','job','92369']).decode()
assert 'JobName=hpy-p126-llfull' in info and 'UserId=yuzelu(' in info
action=ROOT/'stage_failure_actions/stop-known-invalid-fixed-PG-92369.json';assert not action.exists()
record={'scope':'Only this task NEW full C trial, proven immovable signal-to-fixed-PG metal contact; not a time/resource cancellation',
 'job':'92369','proof':str(proof),'proof_sha256':sha(proof),'known_direct_short_pins':r['direct_contact_pin_count'],'rectangle_pairs':r['direct_contact_rectangle_pairs'],
 'original_source_preserved':True,'all_checkpoints_and_logs_preserved':True,'other_jobs_untouched':True,'before_scontrol':info,
 'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'action':'PENDING_STATE_CHECK'}
if 'JobState=RUNNING' in info or 'JobState=PENDING' in info:
    record['action']='STOP_THIS_KNOWN_INVALID_NEW_VARIANT_AFTER_EXACT_PROOF'
    action.write_text(json.dumps(record,indent=2)+'\n')
    subprocess.run(['scancel','92369'],check=True)
else:record['action']='ALREADY_TERMINAL_NO_CANCEL'
record['after_scontrol']=subprocess.check_output(['scontrol','show','job','92369']).decode()
action.write_text(json.dumps(record,indent=2)+'\n')
print(record['action'],record['job'],record['known_direct_short_pins'])
