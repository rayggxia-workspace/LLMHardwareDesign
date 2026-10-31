"""Retire only two verified, unstarted Issue143 dependency handles."""
import json, subprocess
base='/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030'
expected={93825:('yzl-bv2-gates',93808,'015','019'),
          93834:('yzl-bv2-pack',93825,'026','026')}
verified=[]
for job,(name,dependency,snapshot,output) in expected.items():
    text=subprocess.check_output(['scontrol','show','job','-o',str(job)],universal_newlines=True)
    fields=dict(x.split('=',1) for x in text.split() if '=' in x)
    assert fields['JobState']=='PENDING' and fields['UserId']=='yuzelu(10011)'
    assert fields['JobName']==name and fields['RunTime']=='00:00:00'
    assert fields['Dependency']==f'afterok:{dependency}(unfulfilled)'
    script='remote_gates.sh' if 'gates' in name else 'remote_bundle.sh'
    assert fields['Command']==f'{base}/snapshots/{snapshot}/project/experiments/block_v2/{script}'
    assert fields['StdOut']==f'{base}/run{output}-{job}.out'
    verified.append(dict(job=job,fields=fields))
for row in verified:
    # Recheck immediately before cancellation; never cancel a started task.
    text=subprocess.check_output(['scontrol','show','job','-o',str(row['job'])],universal_newlines=True)
    fields=dict(x.split('=',1) for x in text.split() if '=' in x)
    assert fields['JobState']=='PENDING' and fields['RunTime']=='00:00:00'
    subprocess.run(['scancel',str(row['job'])],check=True)
print(json.dumps(dict(retired=verified,reason='Replace initial unmeasured 192GiB/worker forecast with explicit measured-scale 64GiB forecast; no EDA job canceled'),indent=2))

