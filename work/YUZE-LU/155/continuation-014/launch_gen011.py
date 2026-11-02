import subprocess,shlex
q=r'''from pathlib import Path
import subprocess,json,hashlib,sys
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155');out=b/'generate-011';old=b/'generate-010';out.mkdir();(out/'source').mkdir();subprocess.run(['tar','-xf',str(b/'source-gen011c.tar'),'-C',str(out/'source')],check=True)
root=Path('/public/home/yuzelu/opt/eda/issue155-sram/overlays');src=root/'generate-010/openram';dst=root/'generate-011/openram'
subprocess.run([sys.executable,str(out/'source/project/experiments/s_sram/initial_dc_overlay.py'),'--source',str(src),'--destination',str(dst),'--receipt',str(out/'runtime-overlay.json')],check=True)
search=json.loads((old/'search-overlay.json').read_text());search['source']=str(src);search['destination']=str(dst);(out/'search-overlay.json').write_text(json.dumps(search,indent=2)+'\n')
run=(old/'run.sh').read_text().replace(str(src),str(dst)).replace('/overlays/generate-010:', '/overlays/generate-011:').replace(str(old/'search-overlay.json'),str(out/'search-overlay.json')).replace(str(b/'generate-008/runtime-overlay.json'),str(out/'runtime-overlay.json'))
run=run.replace('mkdir -p','export S_SRAM_CHARACTERIZATION_AUDIT="'+str(out/'char-audit')+'"\nmkdir -p');(out/'run.sh').write_text(run)
script=(old/'job.sbatch').read_text().replace(str(old),str(out));(out/'job.sbatch').write_text(script)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();job=subprocess.check_output(['sbatch','--parsable','--output='+str(out/'slurm-%j.log'),str(out/'job.sbatch')],universal_newlines=True).strip()
d=dict(job_id=job,source_commit='SOURCE_COMMIT',archive_sha256=sha(b/'source-gen011c.tar'),runtime_overlay_sha256=sha(out/'runtime-overlay.json'),search_overlay_sha256=sha(out/'search-overlay.json'),cpus=4,scope='Fresh complete WPR2/25 physical generation and native characterization with initial DC, native Gear/default iteration budget/tolerances, content-addressed inputs and outputs. Old producer retained, no previous qualification transferred.')
(out/'submission.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
'''
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();q=q.replace('SOURCE_COMMIT',commit)
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
