from pathlib import Path
import subprocess,json,hashlib,os,time
out=Path(__file__).parent;source=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/source-135');gds=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/pg-strong-delivery-01/control_status/6_final.gds');expected='4c95b736f85ab9cd708dcc7a23778960d4749f49dad660933fa92600f466d90f'
assert os.environ.get('SLURM_JOB_ID')and len(os.sched_getaffinity(0))<=16
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(gds)==expected
rows=[]
for mode,flags in [('batch',['klayout','-b']),('batch-offscreen',['env','QT_QPA_PLATFORM=offscreen','klayout','-b']),('gui-offscreen',['env','QT_QPA_PLATFORM=offscreen','klayout','-z'])]:
 p=out/(mode+'.py');image=out/(mode+'.png')
 p.write_text('import pya\nv=pya.LayoutView()\nv.load_layout('+repr(str(gds))+',0)\nv.max_hier()\nv.add_missing_layers()\nv.zoom_fit()\nv.save_image('+repr(str(image))+',600,600)\n')
 command=flags+['-r',str(p)];start=time.time()
 with(out/(mode+'.log')).open('w')as log:result=subprocess.run(command,cwd=out,stdout=log,stderr=subprocess.STDOUT)
 rows.append(dict(mode=mode,command=command,returncode=result.returncode,seconds=time.time()-start,script_sha256=sha(p),image_sha256=sha(image)if image.exists()else None,log_sha256=sha(out/(mode+'.log'))))
assert sha(gds)==expected
r=dict(passed=all(row['returncode']==0 for row in rows),diagnostic_only=True,native_leaf_qualified=False,whole_system_qualified=False,job=os.environ['SLURM_JOB_ID'],source_manifest_sha256=sha(source/'source-manifest.json'),geometry_join_source_sha256=sha(source/'project/experiments/control_v1/system_geometry_gds.py'),worker_sha256=sha(Path(__file__)),input_gds=str(gds),input_gds_sha256=expected,rows=rows)
(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
