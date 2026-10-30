"""Replace only four unstarted own analysis jobs with stricter lineage guards.

Physical jobs and their immutable drivers never change. No elapsed-time limit.
The new analysis additionally matches exact child receipt hashes for all controls.
"""
import datetime,json,re,subprocess
from run_exports import ROOT

old=['92467','92468','92472','92473'];record_path=ROOT/'stage_failure_actions/supersede-unstarted-parent-STA-r02.json';assert not record_path.exists()
before={}
for job in old:
    text=subprocess.check_output(['scontrol','show','job',job]).decode()
    assert 'JobState=PENDING' in text and 'UserId=yuzelu(' in text
    assert 'JobName=hpy-p126-parentSTA' in text or 'JobName=hpy-p126-ctrlSTA' in text
    assert 'WorkDir='+str(ROOT) in text and 'parent_rc_sta_job.sh' in text
    before[job]=text
assert not (ROOT/'parent_rc_sta/r01').exists() and not (ROOT/'parent_rc_sta/r01-extra').exists()
assert not (ROOT/'parent_rc_sta/r02').exists()
driver=ROOT/'drivers/parent-STA-r02/code';assert (driver/'driver_commit.txt').exists()
record={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reason':'Only unstarted own post-analysis jobs superseded with exact physical+receipt SHA model matching, full boundary-control support and explicit external IO constraint gaps',
 'before':before,'cancelled_unstarted_analysis_jobs':[],'replacement_jobs':[],'physical_jobs_and_other_jobs_untouched':True}
record_path.write_text(json.dumps(record,indent=2)+'\n')
for job in old:
    subprocess.run(['scancel',job],check=True);record['cancelled_unstarted_analysis_jobs'].append(job);record_path.write_text(json.dumps(record,indent=2)+'\n')
for parent_rev,design,focus,deps in [('r07','opentpu','act','92441:92465:92470'),('ll-r01','llaccel','gemm','92458:92466:92471')]:
    command=['sbatch','--job-name=hpy-p126-parentSTA','--dependency=afterany:'+deps,'--output='+str(ROOT/'logs'/('parent-STA-'+design+'-r02-%j.log')),
      '--export=ALL,PINXY_DRIVER_DIR='+str(driver),str(driver/'parent_rc_sta_job.sh'),parent_rev,design,focus,'r02','A','A_replay','A_child_replay','Aopt','B','C']
    response=subprocess.check_output(command).decode();job=re.search(r'Submitted batch job (\d+)',response);assert job,response
    record['replacement_jobs'].append({'job':job[1],'design':design,'command':command,'readback':subprocess.check_output(['scontrol','show','job',job[1]]).decode()})
    record_path.write_text(json.dumps(record,indent=2)+'\n')
print('REPLACED_ONLY_UNSTARTED_ANALYSIS_JOBS',','.join(r['job'] for r in record['replacement_jobs']))
