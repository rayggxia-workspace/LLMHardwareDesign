import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,os,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');s=b/'source-137';assert(s/'freeze-import.json').exists()
old=b/'s-escape-qualified-02/1350';q=b/'s-escape-qualified-03/1350';assert not q.exists();q.mkdir(parents=True)
for op in ['native','selected-native']:(q/op).symlink_to(old/op)
selected=q/'selected-native';early=b/'s-escape-pg-compute-01/1350/wrapper';queue=b/'dynamic-05/node2/pending';rows=[]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def append(name,script,args,deps,out,memory):
 p=queue/(name+'.json');assert not p.exists()and not out.exists()
 spec=dict(script=script,source_root=str(s),forecast_gib=memory,requires=list(map(str,deps)),args=list(map(str,args+['--out',out])))
 tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(spec));os.rename(str(tmp),str(p));rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
wrapper=q/'pg-wrapper';physical=q/'pg-physical';timing=q/'pg-timing';delivery=q/'pg-delivery'
append('00-c0-s1350-pg-rebind137','pg_fixed_access.py',['--manifest',selected/'physical.json','--leaf','block_feed_s_macro','--reuse-computation',early],[selected/'receipt.json',early/'receipt.json'],wrapper,64)
common=['--manifest',selected/'physical.json','--leaf','block_feed_s_macro','--wrapper',wrapper]
append('00-e-s1350-pg-physical137','pg_fixed_timing.py',common+['--physical-only'],[wrapper/'receipt.json'],physical,64)
append('00-e-s1350-pg-timing137','pg_fixed_timing.py',common,[wrapper/'receipt.json'],timing,64)
append('00-f-s1350-pg-delivery137','pg_fixed_timing.py',common+['--deliver','--physical-check',physical,'--timing-check',timing],[physical/'receipt.json',timing/'receipt.json'],delivery,32)
record=b/'route-selection-102/s1350-pg-parallel-join-source137.json';assert not record.exists()
record.write_text(json.dumps(dict(time=time.time(),tasks=rows,source_manifest_sha256=sha(s/'source-manifest.json'),scope='Same S1350 physical implementation. Early actual PG full-deck computation overlaps native gates. Exact six-file identity and actual four successful native gates required before geometry reuse; then fresh PG physical/RC/300MHz/delivery. No original spec edited, no qualification from unfinished work.'),indent=2))
print(json.dumps(dict(appended=4,record=str(record),same_hardware=True)))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
