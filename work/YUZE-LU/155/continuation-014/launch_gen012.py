import subprocess,shlex
q=r'''from pathlib import Path
import subprocess,json,hashlib,sys
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155');old=b/'generate-011';out=b/'generate-012';control=json.loads((b/'grid-control-001/proof/receipt.json').read_text());assert control['passed']
out.mkdir();(out/'source').mkdir();subprocess.run(['tar','-xf',str(b/'source-grid012.tar'),'-C',str(out/'source')],check=True)
root=Path('/public/home/yuzelu/opt/eda/issue155-sram/overlays');src=root/'generate-011/openram';dst=root/'generate-012/openram'
subprocess.run([sys.executable,str(out/'source/project/experiments/s_sram/parallel_grid_overlay.py'),'--source',str(src),'--destination',str(dst),'--receipt',str(out/'grid-overlay.json')],check=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();runtime=json.loads((old/'runtime-overlay.json').read_text());runtime['inherited_from']=dict(path=str(old/'runtime-overlay.json'),sha256=sha(old/'runtime-overlay.json'));runtime['destination']=str(dst);(out/'runtime-overlay.json').write_text(json.dumps(runtime,indent=2)+'\n')
search=json.loads((b/'generate-010/search-overlay.json').read_text());search['destination']=str(dst);search['inherited_from']=dict(path=str(b/'generate-010/search-overlay.json'),sha256=sha(b/'generate-010/search-overlay.json'));(out/'search-overlay.json').write_text(json.dumps(search,indent=2)+'\n')
run=(old/'run.sh').read_text().replace(str(src),str(dst)).replace('/overlays/generate-011:', '/overlays/generate-012:').replace(str(old/'runtime-overlay.json'),str(out/'runtime-overlay.json')).replace(str(old/'search-overlay.json'),str(out/'search-overlay.json')).replace(str(old/'char-audit'),str(out/'char-audit'))
run=run.replace('mkdir -p','export S_SRAM_GRID_OVERLAY_RECEIPT="'+str(out/'grid-overlay.json')+'"\nexport S_SRAM_GRID_WORKERS=6\nmkdir -p');(out/'run.sh').write_text(run)
script=(old/'job.sbatch').read_text().replace(str(old),str(out)).replace('--cpus-per-task=4','--cpus-per-task=8').replace('--env SLURM_JOB_ID="$SLURM_JOB_ID"','--env SLURM_JOB_ID="$SLURM_JOB_ID" --env SLURM_CPUS_PER_TASK=8');(out/'job.sbatch').write_text(script)
job=subprocess.check_output(['sbatch','--parsable','--output='+str(out/'slurm-%j.log'),str(out/'job.sbatch')],universal_newlines=True).strip()
d=dict(job_id=job,source_commit='4b459693',archive_sha256=sha(b/'source-grid012.tar'),grid_control_sha256=sha(b/'grid-control-001/proof/receipt.json'),runtime_overlay_sha256=sha(out/'runtime-overlay.json'),grid_overlay_sha256=sha(out/'grid-overlay.json'),search_overlay_sha256=sha(out/'search-overlay.json'),cpus=8,grid_workers=6,scope='Fresh complete WPR2/25 generation; initial DC and native Gear/default iteration budget/tolerances/checks. Serial native min-period/leakage, then six independent native grid workers with dynamic backfill. Old running producers retained.')
(out/'submission.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
