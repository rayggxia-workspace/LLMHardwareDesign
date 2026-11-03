import subprocess,shlex
q="""from pathlib import Path
import json,hashlib,collections,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');p=b/'r256-composition-359/topology/boundary-graph.json';g=json.loads(p.read_text());rows=g['boundary_links']['links'];tot=collections.Counter();detail=[]
for r in rows:
 n=r['padded_input_lanes'];tot[r['source_instance']]+=n
 if n:detail.append(dict(instance=r['instance'],source=r['source_instance'],unused_input_pins=n,padded_from_net=r['lanes'][0]['input_bit'],reset_bank=r['reset_bank_output']))
out=b/'r256-unused-link-input-load-450';assert not out.exists();out.mkdir();d=dict(captured_at=time.time(),graph_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),links=len(rows),links_with_padding=len(detail),unused_input_pins=sum(tot.values()),by_source=dict(tot),rows=detail,whole_system_qualified=False,scope='Actual currently generated Link8 unused input lanes repeat first live payload bit; unused outputs have no original consumers. Their real input pin capacitance still loads source. This is a topology diagnosis, not a fixed circuit or proof that removing the load meets any physical gate. Preserve all old evidence.');(out/'receipt.json').write_text(json.dumps(d,indent=2));print(json.dumps({k:d[k]for k in ['links','links_with_padding','unused_input_pins','by_source']}));print('net7453',json.dumps([r for r in detail if r['padded_from_net']==7453]))
"""
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
