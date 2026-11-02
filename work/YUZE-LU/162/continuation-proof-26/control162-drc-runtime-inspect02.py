import subprocess,shlex
q=r'''from pathlib import Path
import json,subprocess,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');out=b/'drc-runtime-inspection-02';assert not out.exists()
details=subprocess.check_output(['scontrol','show','job','95341','-o'],universal_newlines=True)
assert 'UserId=yuzelu(10011)'in details and 'JobName=yzl-ctl162-smem2 'in details and 'NodeList=node2 'in details
out.mkdir()
command=['srun','--jobid=95341','--exclusive','-n1','-c1','--cpu-bind=cores','/public/software/singularity-ce-4.3.4/bin/singularity','exec','--cleanenv','--bind','/public/home/yuzelu','/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif','cat','/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc']
data=subprocess.check_output(command);(out/'original-deck.lydrc').write_bytes(data)
(out/'receipt.json').write_text(json.dumps(dict(passed=True,diagnostic_only=True,command=command,time=time.time(),job_verified=details,deck_sha256=hashlib.sha256(data).hexdigest(),scope='Read original complete deck within own Slurm allocation only; no source/gate/task/geometry changed, no hardware qualification'),indent=2))
assert data.startswith(b'<?xml');old=(b/'drc-runtime-inspection-01/original-deck.lydrc').read_bytes();assert old.endswith(data);print(json.dumps(dict(deck_sha256=hashlib.sha256(data).hexdigest(),old_stdout_prefix=old[:-len(data)].decode(),unchanged_original_rule_deck=True)))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
