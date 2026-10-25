"""Read-only routed path and wire-length representation diagnostic."""
import argparse,re,csv,collections
from decimal import Decimal
from common import *
p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);sm=artifacts(a.stage);m={'source':sources(),'resources':resource_snapshot(),'stage_manifest_sha256':sha(a.stage/'manifest.json')}
seg=(a.stage/'route.segments').read_text();sums={};unique={}
for match in re.finditer(r'(?ms)^(\S+)\n\(\n(.*?)^\)\s*$',seg):
 n,body=match.groups();length=0;seen=set()
 for line in body.strip().splitlines():
  x,y,l,x2,y2,l2=line.split();x,y,x2,y2=map(int,(x,y,x2,y2))
  if l==l2:length+=abs(x-x2)+abs(y-y2);seen.add(tuple(sorted(((x,y,l),(x2,y2,l2)))))
 sums[n]=Decimal(length)/2000;unique[n]=sum((Decimal(abs(a[0]-b[0])+abs(a[1]-b[1]))/2000 for a,b in seen),Decimal(0))
errors=[]
for line in (a.stage/'wirelength.csv').read_text().splitlines()[1:]:
 _,n,v,_=line.split();diff=Decimal(v)-sums[n]
 if abs(diff)>Decimal('.005'):errors.append({'net':n,'reported_um':v,'segment_sum_um':str(sums[n]),'unique_segment_sum_um':str(unique[n]),'difference_um':str(diff)})
records=list(csv.DictReader((a.stage/'hold-load10.tsv').read_text().splitlines(),delimiter='\t'));bad=[x for x in records if Decimal(x['slack'])<0]
put(a.out/'diagnosis.json',{'wirelength_differences':errors,'hold_negative_endpoints':bad,'stage_manifest_sha256':m['stage_manifest_sha256']})
lines=['set_thread_count 8',f'read_liberty {{{LIB}}}',f'read_db {{{a.stage}/final.odb}}',f'read_sdc {{{a.stage}/final.sdc}}',f'read_spef {{{a.stage}/route.spef}}','puts "BEGIN_ROUTED_HOLD_PATHS"','report_checks -path_delay min -group_path_count 20 -format full_clock_expanded -fields {capacitance slew fanout input} -digits 9','puts "END_ROUTED_HOLD_PATHS"']
s=a.out/'probe.tcl';s.write_text(tcl_script(lines));command(a.out,'probe',[OR,'-exit',s],300);m['status']='ROUTED_DIAGNOSTICS_EXECUTED_NOT_REPAIRED';manifest(a.out,m)
