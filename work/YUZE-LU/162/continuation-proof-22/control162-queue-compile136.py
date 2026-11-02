import subprocess,shlex
q=r'''from pathlib import Path
import json,os,time,hashlib
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');s=b/'source-136';assert(s/'freeze-import.json').exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
record=b/'route-selection-102/s-compile-parallel-source136.json';assert not record.exists()
queue=b/'dynamic-05/node4'
for part in ['pending','commands','results']:(queue/part).mkdir(parents=True,exist_ok=True)
raw=b/'s-escape-repair-01/candidate-1350';old=b/'s-escape-gates-01/1350';g=b/'s-escape-gates-02/1350';g.mkdir(parents=True)
for op in ['sealed','physical','drc']:(g/op).symlink_to(old/op)
sealed=old/'sealed';qual=b/'s-escape-qualified-02/1350';rows=[]
def append(name,script,args,deps,out,memory):
 p=queue/'pending'/(name+'.json');assert not p.exists()and not out.exists()
 spec=dict(script=script,source_root=str(s),forecast_gib=memory,requires=list(map(str,deps)),args=list(map(str,args+['--out',out])))
 temp=p.with_suffix('.tmp');temp.write_text(json.dumps(spec));os.rename(str(temp),str(p));rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
common=['--native-s','--producer',raw,'--source-root',s,'--sealed',sealed]
append('00-a-s1350-ungrouped136','gates.py',['function']+common+['--ungrouped-native-s'],[sealed/'receipt.json',raw/'receipt.json'],g/'function',128)
# The immutable complete view is a computation dependency; final_formal still
# unconditionally joins the actual completed function receipt before passing.
append('00-b-s1350-parallel-formal136','gates.py',['formal']+common+['--gates',g],[sealed/'receipt.json',raw/'receipt.json',g/'function/physical-functional-proof.json'],g/'formal',256)
delivery=qual/'native';selection=qual/'selected-native';wrapper=qual/'pg-wrapper';physical=qual/'pg-physical';timing=qual/'pg-timing';pg=qual/'pg-delivery';original=b/'composition-drive-pg-01/selected'
append('00-c-s1350-native136','gates.py',['deliver']+common+['--gates',g],[g/o/'receipt.json'for o in ['physical','drc','function','formal']],delivery,32)
append('00-c-s1350-select136','select_leaves.py',['--physical',original/'physical.json','--functions',original/'functions.json','--s-internal-delivery',delivery],[delivery/'receipt.json'],selection,16)
append('00-d-s1350-wrapper136','pg_fixed_access.py',['--manifest',selection/'physical.json','--leaf','block_feed_s_macro'],[selection/'receipt.json'],wrapper,64)
for label,out,flags in [('physical',physical,['--physical-only']),('timing',timing,[])]:
 append('00-e-s1350-pg-'+label+'136','pg_fixed_timing.py',['--wrapper',wrapper,'--manifest',selection/'physical.json','--leaf','block_feed_s_macro']+flags,[wrapper/'receipt.json'],out,64)
append('00-f-s1350-pg-delivery136','pg_fixed_timing.py',['--wrapper',wrapper,'--manifest',selection/'physical.json','--leaf','block_feed_s_macro','--deliver','--physical-check',physical,'--timing-check',timing],[physical/'receipt.json',timing/'receipt.json'],pg,32)
record.write_text(json.dumps(dict(time=time.time(),source_manifest_sha256=sha(s/'source-manifest.json'),tasks=rows,existing_geometry_gates=str(old),same_raw_source=str(raw),reason='Same S1350 hardware and exact seal/physical/DRC reused, no repeated raw final LEС or changed threshold. Existing supported output-groups0 compilation and strict formal start on full immutable physical view; formal acceptance still joins real successful three-initial function receipt. All older immutable tasks preserved, new node4 controller starts only after exact sealed source passes.'),indent=2))
print(json.dumps(dict(appended=len(rows),record=str(record),same_hardware=True,new_controller_started=False)))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
