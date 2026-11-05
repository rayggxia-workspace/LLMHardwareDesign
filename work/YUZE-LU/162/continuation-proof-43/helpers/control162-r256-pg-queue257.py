import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');source=b/'source-256';native=b/'r256-native-reuse-251';pg=b/'r256-fixed-pg-257';record=b/'route-selection-102/sready257-r256-native-pg';assert not record.exists();rows=[]
def add(name,script,args,deps,out,memory):
 p=b/'dynamic-06/node7/pending'/(name+'.json');assert not p.exists()and not out.exists()
 spec=dict(script=script,source_root=str(source),forecast_gib=memory,requires=list(map(str,deps)),args=list(map(str,args))+['--out',str(out)])
 p.write_text(json.dumps(spec));rows.append(dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),spec=spec))
common=['--manifest',native/'physical.json','--leaf','r_stream_local']
add('00-e-sready257-pg-r256','pg_fixed_access.py',common,[native/'receipt.json'],pg/'wrapper',64)
for mode in ['physical','timing']:
 add('00-f-sready257-'+mode+'-r256','pg_fixed_timing.py',common+['--wrapper',pg/'wrapper']+(['--physical-only']if mode=='physical'else[]),[pg/'wrapper/receipt.json'],pg/'checks'/mode,64)
add('00-g-sready257-deliver-r256','pg_fixed_timing.py',common+['--wrapper',pg/'wrapper','--deliver','--physical-check',pg/'checks/physical','--timing-check',pg/'checks/timing'],[pg/'checks'/mode/'receipt.json'for mode in ['physical','timing']],pg/'delivery',64)
record.mkdir();(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,whole_system_qualified=False,scope='Exact qualified R256 native evidence reuse with actual complete ODB signal identity and original821pin inventory; then original fixed-PG full DRC/XOR/physical/new RC/300MHz/full-view identity/delivery. Existing control-leaf positive protection-cell check unchanged; R-specific zero ANTENNA requires actual ODB count zero and exact all-signal connectivity. Original R native geometry preserved, whole-macro placement phase explicit. All existing memory/16CPU/eight-parent limits unchanged.'),indent=2));print(json.dumps(dict(queued=len(rows))))
'''
compile(q,'r256_reuse_queue249','exec')
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=35).decode())