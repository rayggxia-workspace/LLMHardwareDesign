"""Cross-bind actual GRT payload and separate electrical counter replay."""
import csv,re
from decimal import Decimal
from common import *
from receive_physical import block

def audit_replay(stage,replay,out):
 sm=artifacts(stage);rm=artifacts(replay);need(rm['status']=='ACTUAL_GRT_RC_REPLAY_AND_ELECTRICAL_COUNTS_EXECUTED'and rm['stage_directory']==str(stage)and rm['stage_manifest_sha256']==sha(stage/'manifest.json'),'same actual stage replay binding')
 for n in('final.odb','final.sdc','route.segments','route.spef','final.json'):need(rm['inputs'][n]==sha(stage/n),'replay source bytes '+n)
 for q in(LIB,TECH,LEF,P/'setRC.tcl'):need(rm['views'][str(q)]==sha(q),'same actual replay physical view')
 need(rm['original_spef_sha256']==sha(stage/'route.spef')and rm['replayed_spef_sha256']==sha(replay/'replay.spef')and sha(stage/'route.spef')==sha(replay/'replay.spef')and rm['byte_identical']is True,'same-tool replay reproduces every original SPEF byte')
 rs=list(csv.DictReader((replay/'counts.tsv').read_text().splitlines(),delimiter='\t'));need(len(rs)==2 and [r['load_fF']for r in rs]==['1','10'],'both replay loads');log=(stage/'flow.log').read_text();counts=[]
 for row in rs:
  er=block(block(log,'BEGIN_SCENARIO_'+row['load_fF'],'END_SCENARIO_'+row['load_fF']),'BEGIN_ELECTRICAL_REPORT','END_ELECTRICAL_REPORT');need(er.strip()!='','executed electrical report not deleted');one={'load_fF':int(row['load_fF'])}
  for label,key in [('max slew','max_slew'),('max capacitance','max_capacitance'),('max fanout','max_fanout')]:
   m=re.search(r'(?m)^'+label+r'\s*$',er);tail=er[m.end():]if m else'';end=re.search(r'(?m)^(max slew|max capacitance|max fanout|max delay/setup|min delay/hold)\s*$',tail);tail=tail[:end.start()]if end else tail;actual=tail.count('(VIOLATED)');need(row[key].isdigit()and int(row[key])==actual,'actual independent '+key+' count matches original report');one[key]=actual
  counts.append(one)
 deltas=[];sumtot=Decimal(0);sumcaps=Decimal(0)
 for m in re.finditer(r'(?ms)^\*D_NET (\S+) (\S+)\n(.*?)^\*END\s*$',(stage/'route.spef').read_text()):
  vals=[Decimal(x.split()[-1])for x in m[3].split('*CAP\n',1)[1].split('*RES\n',1)[0].strip().splitlines()];total=Decimal(m[2]);caps=sum(vals,Decimal(0));sumtot+=total;sumcaps+=caps;deltas.append({'net':m[1],'D_NET_fF':str(total),'written_CAP_sum_fF':str(caps),'difference_fF':str(total-caps)})
 put(out/'rc-cap-deltas.json',deltas)
 return {'status':'PASS_SAME_TOOL_BYTE_REPLAY_AND_INDEPENDENT_ELECTRICAL_COUNTS','replay_manifest_sha256':sha(replay/'manifest.json'),'replay_source_commit':rm['source']['commit'],'counts':counts,'D_NET_total_fF':str(sumtot),'written_CAP_total_fF':str(sumcaps),'difference_fF':str(sumtot-sumcaps),'numeric_scope':'Tool reproducibility only, not independent RC solution. Installed GRT writer omits ground cap on pin nodes while D_NET includes it; exported SPEF is not a lossless substitute for in-memory estimate.','delta_artifact':str(out/'rc-cap-deltas.json')}
