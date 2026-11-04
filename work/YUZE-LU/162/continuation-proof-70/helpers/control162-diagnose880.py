from pathlib import Path
import subprocess,shlex,json,time
q=r'''from pathlib import Path
import json,hashlib
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');p=b/'r256-native-prefix-path-diagnostic-873/native-prefix';paths=list(p.glob('case-*/diagnostic.json'));rows=[]
for f in paths:
 d=json.loads(f.read_text());rows.append((d['excess_occupancy'],d['case'],f,d))
if not rows:print(json.dumps(dict(ready=False,cases=0)))
else:
 rows.sort();_,_,f,d=rows[0];graph_path=b/'r256-composition-453/topology/boundary-graph.json';g=json.loads(graph_path.read_text());nets=sorted({name for c in d['conflict_cells']for name in c['nets']});input_rows={}
 with Path(d['original_input']).open()as inp:
  header=inp.readline()
  for line in inp:
   cols=line.split()
   if cols[0]in nets:input_rows[cols[0]]=cols
 connections={n:g['connections'].get(n[4:])for n in nets};print(json.dumps(dict(ready=True,cases=len(rows),selected_case=d['case'],excess=d['excess_occupancy'],conflict_cells=d['conflict_cells'],input_rows=input_rows,connections=connections,diagnostic_path=str(f),diagnostic_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),snapshot_path=d['snapshot_path'],snapshot_sha256=d['snapshot_sha256'],native_log_filtered_byte_exact=d['native_log_filtered_byte_exact'],main_failure_log_byte_exact=d['main_failure_log_byte_exact'],whole_system_qualified=False)))
'''
raw=subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]);out=Path(__file__).parent/'control162-native-conflicts880';out.mkdir(exist_ok=True);(out/(str(time.time_ns())+'.json')).write_bytes(raw);d=json.loads(raw);print(json.dumps(dict(ready=d['ready'],cases=d['cases'],selected=d.get('selected_case'),excess=d.get('excess'),cells=d.get('conflict_cells'),nets=sorted(d.get('input_rows',{})))))
