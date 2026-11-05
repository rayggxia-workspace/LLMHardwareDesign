import subprocess,shlex
q=r'''from pathlib import Path
import json,os,time,hashlib
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');s=b/'source-133'
assert(s/'freeze-import.json').exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
record=b/'route-selection-102/s-escape-repair-source133.json';assert not record.exists()
queue=b/'dynamic-05/node2'
for part in ['pending','commands','results']:(queue/part).mkdir(parents=True,exist_ok=True)
rows=[]
def append(name,script,args,deps,out,memory):
 p=queue/'pending'/(name+'.json');assert not p.exists()and not out.exists()
 spec=dict(script=script,source_root=str(s),forecast_gib=memory,requires=list(map(str,deps)),args=list(map(str,args+['--out',out])))
 temp=p.with_suffix('.tmp');temp.write_text(json.dumps(spec));os.rename(str(temp),str(p))
 rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
prior=b/'s-internal-drive-02/candidate-1181';failed=b/'s-final-evidence-02/1181/drc'
assert json.loads((prior/'receipt.json').read_text())['passed']and json.loads((failed/'receipt.json').read_text())['passed']is False
raw=b/'s-escape-repair-01/candidate-1330';g=b/'s-escape-gates-01/1330';sealed=g/'sealed';qual=b/'s-escape-qualified-01/1330'
append('00-a-s1330-escape','run.py',['--model','native_s_escape_repair','--s-native-source',prior,'--s-escape-drc',failed,'--physical'],[prior/'receipt.json',b/'s-final-evidence-02/1181/physical/receipt.json'],raw,256)
for op in ['seal','physical','drc','function','formal']:
 out=sealed if op=='seal'else g/op;deps=[raw/'receipt.json',b/'s-internal-rtl-smoke-02/receipt.json']
 args=[op,'--native-s','--producer',raw,'--source-root',s]
 if op!='seal':args+=['--sealed',sealed];deps.append(sealed/'receipt.json')
 if op=='formal':args+=['--gates',g];deps.append(g/'function/receipt.json')
 append('00-b-s1330-'+op,'gates.py',args,deps,out,256 if op=='formal'else 128 if op=='function'else 64)
delivery=qual/'native';selection=qual/'selected-native';wrapper=qual/'pg-wrapper';physical=qual/'pg-physical';timing=qual/'pg-timing';pg=qual/'pg-delivery';original=b/'composition-drive-pg-01/selected'
append('00-c-s1330-native','gates.py',['deliver','--native-s','--producer',raw,'--source-root',s,'--sealed',sealed,'--gates',g],[g/o/'receipt.json'for o in ['physical','drc','function','formal']],delivery,32)
append('00-c-s1330-select','select_leaves.py',['--physical',original/'physical.json','--functions',original/'functions.json','--s-internal-delivery',delivery],[delivery/'receipt.json'],selection,16)
append('00-d-s1330-wrapper','pg_fixed_access.py',['--manifest',selection/'physical.json','--leaf','block_feed_s_macro'],[selection/'receipt.json'],wrapper,64)
for label,out,flags in [('physical',physical,['--physical-only']),('timing',timing,[])]:
 append('00-e-s1330-pg-'+label,'pg_fixed_timing.py',['--wrapper',wrapper,'--manifest',selection/'physical.json','--leaf','block_feed_s_macro']+flags,[wrapper/'receipt.json'],out,64)
append('00-f-s1330-pg-delivery','pg_fixed_timing.py',['--wrapper',wrapper,'--manifest',selection/'physical.json','--leaf','block_feed_s_macro','--deliver','--physical-check',physical,'--timing-check',timing],[physical/'receipt.json',timing/'receipt.json'],pg,32)
record.write_text(json.dumps(dict(time=time.time(),source_manifest_sha256=sha(s/'source-manifest.json'),tasks=rows,source_receipt_sha256=sha(prior/'receipt.json'),reason='Actual final S1181 all-endpoint300MHz/electrical passed, four M10 same-net spacing failures only. Bounded pre-freeze escape simplification; fresh RC and all gates/PG mandatory. No GRT reset delay promoted, no old specs changed.'),indent=2))
print(json.dumps(dict(appended=len(rows),record=str(record))))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
