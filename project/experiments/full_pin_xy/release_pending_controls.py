"""Release only scheduling dependencies of two verified unstarted own controls.

No new jobs, cancellation, active-job edit, driver/input/output or CPU changes.
These two designs have no data dependency on the preceding VECTOR comparison.
"""
import datetime,json,subprocess
from run_exports import ROOT

targets=[('92392','hpy-p126-otctrl','opentpu_aux'),('92393','hpy-p126-llctrl','llaccel_aux')]
proof=ROOT/'stage_failure_actions/release-unstarted-independent-controls.json';assert not proof.exists()
before={}
for job,name,case in targets:
    text=subprocess.check_output(['scontrol','show','job',job]).decode()
    assert 'JobState=PENDING' in text and 'JobName='+name in text and 'UserId=yuzelu(' in text
    assert 'WorkDir='+str(ROOT) in text and 'drivers/full-controls-r04/code/trial_job.sh' in text
    for plan in ['A_replay','Aopt','B']:assert not (ROOT/'trials/full-controls-r04'/(case+'-'+plan)).exists()
    before[job]=text
record={'scope':'Only two verified unstarted independent own controls; release scheduling dependency, keep existing jobs/drivers/inputs/output locations/CPU limits',
 'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'before':before,'changes':[],'other_active_jobs_untouched':True}
proof.write_text(json.dumps(record,indent=2)+'\n')
for job,name,case in targets:
    subprocess.run(['scontrol','update','JobId='+job,'Dependency='],check=True)
    after=subprocess.check_output(['scontrol','show','job',job]).decode()
    assert 'Dependency=(null)' in after and 'JobName='+name in after
    record['changes'].append({'job':job,'case':case,'after':after,'cancelled':False,'new_job_submitted':False})
    proof.write_text(json.dumps(record,indent=2)+'\n')
print('RELEASED_ONLY_UNSTARTED_SCHEDULING_DEPENDENCIES',','.join(j for j,n,c in targets))
