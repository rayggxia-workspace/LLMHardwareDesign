import os,json,hashlib,subprocess,time,shutil,xml.etree.ElementTree as E
from pathlib import Path
assert os.environ.get('SLURM_JOB_ID')
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155');out=Path.cwd();name='s_sram_256x128_freepdk45';source=b/'generate-008/generation/bank'/ (name+'.gds');gds=out/(name+'.gds');r=dict(passed=False,qualified=False,commands=[],inputs={})
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save():(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
def run(cmd,log):
 t=time.monotonic()
 with (out/log).open('w') as f:p=subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT)
 r['commands'].append(dict(argv=list(map(str,cmd)),returncode=p.returncode,seconds=time.monotonic()-t,log=log,sha256=sha(out/log)));save();assert p.returncode==0
try:
 for p in [source,out/'source/project/experiments/s_sram/repair_via2.py']:r['inputs'][str(p)]=sha(p)
 run(['klayout','-b','-r','source/project/experiments/s_sram/repair_via2.py','-rd','SOURCE='+str(source),'-rd','OUTPUT='+str(gds),'-rd','RECEIPT='+str(out/'geometry-proof.json')],'eco.log')
 for src in [b/'macro-lvs-001/freepdk45.lylvs',Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc'),b/'generate-008/generation/bank'/ (name+'.lvs.sp')]:
  shutil.copyfile(src,out/src.name);assert sha(src)==sha(out/src.name);r['inputs'][str(src)]=sha(src)
 commands=[(['klayout','-b','-r','freepdk45.lylvs','-rd','input='+str(gds),'-rd','schematic='+str(out/(name+'.lvs.sp')),'-rd','report='+str(out/'macro.lvsdb'),'-rd','target_netlist='+str(out/'extracted.spice')],'lvs.log'),(['klayout','-b','-r','FreePDK45.lydrc','-rd','in_gds='+str(gds),'-rd','report_file='+str(out/'full.lyrdb')],'drc.log')]
 launched=[]
 for cmd,log in commands:
  f=(out/log).open('w');launched.append((subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT),f,cmd,log,time.monotonic()))
 for p,f,cmd,log,t in launched:
  rc=p.wait();f.close();r['commands'].append(dict(argv=cmd,returncode=rc,seconds=time.monotonic()-t,log=log,sha256=sha(out/log)));save()
 text=(out/'lvs.log').read_text();items=E.parse(out/'full.lyrdb').findall('.//items/item')
 r.update(lvs_match='CONGRATULATIONS! Netlists match.' in text and 'ERROR' not in text,drc_items=len(items),gds_sha256=sha(gds))
 r['passed']=r['lvs_match'] and not items and all(c['returncode']==0 for c in r['commands']);save();assert r['passed']
finally:save()
