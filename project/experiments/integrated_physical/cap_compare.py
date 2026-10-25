"""Read-only exact routed net comparison for a frozen driver across stages."""
import argparse,re
from decimal import Decimal
from common import *
from receive_physical import block,def_name
from route_audit import incidence
p=argparse.ArgumentParser();p.add_argument('--stages',nargs='+',type=Path,required=True);p.add_argument('--driver',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);inst,pin=a.driver.rsplit('/',1);rows=[]
for stage in a.stages:
 sm=artifacts(stage);mods=load(stage/'final.json')['modules'];need(len(mods)==1,'single integrated cut');net=next(iter(mods.values()));c=net['cells'][inst];need(c['port_directions'][pin]=='output'and len(c['connections'][pin])==1,'scalar driver');refs,_,_=incidence(net);b=c['connections'][pin][0]
 dn=None
 for name,body in re.findall(r'(?s)-\s+(\S+)\s+(.*?);',block((stage/'placed.def').read_text(),'\nNETS ','END NETS').split(';',1)[1]):
  ps={(def_name(n),def_name(q))for n,q in re.findall(r'\(\s*(\S+)\s+(\S+)\s*\)',body.split('+',1)[0])}
  if (inst,pin)in ps:need(dn is None,'unique driver DEF net');dn=def_name(name)
 need(dn is not None,'driver physical net');spef=(stage/'route.spef').read_text();matches=[x for x in re.finditer(r'(?ms)^\*D_NET (\S+) (\S+)\n(.*?)^\*END\s*$',spef)if re.sub(r'\\(.)',r'\1',x[1])==dn];need(len(matches)==1,'one driver RC net');m=matches[0];ground=sum((Decimal(x.split()[-1])for x in m[3].split('*CAP\n',1)[1].split('*RES\n',1)[0].strip().splitlines()),Decimal(0));segs=[x for x in re.finditer(r'(?ms)^(\S+)\n\(\n(.*?)^\)\s*$',(stage/'route.segments').read_text())if re.sub(r'\\(.)',r'\1',x[1])==dn];need(len(segs)==1,'one driver route');wire=Decimal(0);vias=0
 for line in segs[0][2].strip().splitlines():
  x,y,l,x2,y2,l2=line.split()
  if l==l2:wire+=Decimal(abs(int(x)-int(x2))+abs(int(y)-int(y2)))/2000
  else:vias+=1
 electrical=block(block((stage/'flow.log').read_text(),'BEGIN_SCENARIO_10','END_SCENARIO_10'),'BEGIN_ELECTRICAL_REPORT','END_ELECTRICAL_REPORT');bad=[line for line in electrical.splitlines()if line.split()and line.split()[0]==a.driver]
 rows.append({'stage':str(stage),'stage_manifest_sha256':sha(stage/'manifest.json'),'driver':a.driver,'master':c['type'],'net':dn,'pin_refs':sorted(refs[b]),'spef_reported_total_cap_fF':m[2],'spef_ground_cap_sum_fF':str(ground),'route_planar_um':str(wire),'route_vias':vias,'electrical_violations':bad})
put(a.out/'comparison.json',{'status':'READONLY_EXACT_DRIVER_ROUTE_COMPARISON','source':sources(),'resources':resource_snapshot(),'rows':rows});print('READONLY_EXACT_DRIVER_ROUTE_COMPARISON')
