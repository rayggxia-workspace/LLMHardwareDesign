from pathlib import Path
import subprocess,json,hashlib,shutil,time,os
assert os.environ.get('SLURM_JOB_ID')
src=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/generate-007/openram-temp')
name='s_sram_256x128_freepdk45'
deck=Path('/public/home/yuzelu/opt/eda/issue155-sram/overlays/generate-007/openram/technology/freepdk45/tech/freepdk45.lylvs')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
record=dict(passed=False,qualified=False,inputs={},job_id=os.environ['SLURM_JOB_ID'],implicit_supply_connections=False)
for p in [src/(name+'.gds'),src/(name+'.sp'),deck]:
 before=sha(p);q=Path.cwd()/p.name;shutil.copyfile(p,q);assert sha(q)==before==sha(p)
 record['inputs'][str(p)]=dict(copy=str(q),sha256=before,bytes=q.stat().st_size)
argv=['klayout','-b','-r',str(Path.cwd()/deck.name),'-rd','input='+str(Path.cwd()/(name+'.gds')),'-rd','schematic='+str(Path.cwd()/(name+'.sp')),'-rd','report='+str(Path.cwd()/'macro.lvsdb'),'-rd','target_netlist='+str(Path.cwd()/'extracted.spice')]
record['argv']=argv;Path('receipt.json').write_text(json.dumps(record,indent=2)+'\n')
start=time.monotonic()
with Path('lvs.log').open('w') as f:r=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT)
text=Path('lvs.log').read_text();record.update(returncode=r.returncode,seconds=time.monotonic()-start,
 explicit_match=text.count('CONGRATULATIONS! Netlists match.')==1,explicit_mismatch='ERROR' in text,
 outputs={str(p):dict(sha256=sha(p),bytes=p.stat().st_size) for p in [Path('lvs.log'),Path('macro.lvsdb'),Path('extracted.spice')] if p.is_file()})
record['passed']=r.returncode==0 and record['explicit_match'] and not record['explicit_mismatch'] and len(record['outputs'])==3
record['scope']='Independent real routed bank GDS vs full transistor schematic, unchanged FreePDK45 LVS deck, no implicit vdd/gnd connections. Macro DRC/characterization and complete S qualification are separate.'
Path('receipt.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2));assert record['passed']
