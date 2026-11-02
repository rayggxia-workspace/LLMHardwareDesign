import subprocess,shlex
q=r'''from pathlib import Path
import subprocess,json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');out=b/'upper-render-preflight-01';assert not out.exists();out.mkdir()
source=b/'source-135';gds=b/'pg-strong-delivery-01/control_status/6_final.gds'
expected='4c95b736f85ab9cd708dcc7a23778960d4749f49dad660933fa92600f466d90f'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();assert sha(gds)==expected
details=subprocess.check_output(['scontrol','show','job','95341','-o'],universal_newlines=True)
assert 'UserId=yuzelu(10011)'in details and 'JobName=yzl-ctl162-smem2 'in details and 'NodeList=node2 'in details
worker=out/'worker.py'
worker.write_text("""from pathlib import Path
import subprocess,json,hashlib,os,time
out=Path(__file__).parent;source=Path('SOURCE');gds=Path('GDS');expected='EXPECTED'
assert os.environ.get('SLURM_JOB_ID')and len(os.sched_getaffinity(0))<=16
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(gds)==expected
rows=[]
for mode,flags in [('batch',['klayout','-b']),('batch-offscreen',['env','QT_QPA_PLATFORM=offscreen','klayout','-b']),('gui-offscreen',['env','QT_QPA_PLATFORM=offscreen','klayout','-z'])]:
 p=out/(mode+'.py');image=out/(mode+'.png')
 p.write_text('import pya\\nv=pya.LayoutView()\\nv.load_layout('+repr(str(gds))+',0)\\nv.max_hier()\\nv.add_missing_layers()\\nv.zoom_fit()\\nv.save_image('+repr(str(image))+',600,600)\\n')
 command=flags+['-r',str(p)];start=time.time()
 with(out/(mode+'.log')).open('w')as log:result=subprocess.run(command,cwd=out,stdout=log,stderr=subprocess.STDOUT)
 rows.append(dict(mode=mode,command=command,returncode=result.returncode,seconds=time.time()-start,script_sha256=sha(p),image_sha256=sha(image)if image.exists()else None,log_sha256=sha(out/(mode+'.log'))))
assert sha(gds)==expected
r=dict(passed=all(row['returncode']==0 for row in rows),diagnostic_only=True,native_leaf_qualified=False,whole_system_qualified=False,job=os.environ['SLURM_JOB_ID'],source_manifest_sha256=sha(source/'source-manifest.json'),geometry_join_source_sha256=sha(source/'project/experiments/control_v1/system_geometry_gds.py'),worker_sha256=sha(Path(__file__)),input_gds=str(gds),input_gds_sha256=expected,rows=rows)
(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\\n');print(json.dumps(r))
""".replace('SOURCE',str(source)).replace('GDS',str(gds)).replace('EXPECTED',expected))
image='/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif'
cmd=['srun','--jobid=95341','--exclusive','-n1','-c16','--cpu-bind=cores','/public/software/singularity-ce-4.3.4/bin/singularity','exec','--cleanenv','--bind','/public/home/yuzelu','--env','SLURM_JOB_ID=95341',image,'bash','-c','source /OpenROAD-flow-scripts/env.sh; exec python3 "$1"','bash',str(worker)]
(out/'launch.json').write_text(json.dumps(dict(time=time.time(),command=cmd,worker_sha256=sha(worker),verified_own_parent=details,scope='Independent accepted small-GDS render mode preflight only. At most another16CPU inside own64CPU node2 allocation; no existing task/spec/source touched, no block/system acceptance.'),indent=2))
print(subprocess.check_output(cmd,universal_newlines=True))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
