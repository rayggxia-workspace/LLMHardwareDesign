"""Read-only all-driver actual cap headroom; no repair or route mutation."""
import argparse,re,sys
from decimal import Decimal
from common import *
from receive_physical import block,library
from route_audit import incidence
sys.path.insert(0,str(ROOT/'project/experiments/electrical_repair'))
from structure import signature_graph,groups,attr
p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--target',type=int,choices=[93,97],required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);sm=artifacts(a.stage);need(sm['stage']in('caprepair','drt'),'frozen actual final stage');net=load(a.stage/'final.json')['modules']['chain'+str(a.target)];lib=library(LIB);canon=signature_graph(net,lib);clock=canon(net['ports']['clk']['bits'][0])[0];refs,dirs,_=incidence(net);pinlimits={}
for typ,body in groups(LIB.read_text(),'cell'):
 for pn,pb in groups(body,'pin'):
  lim=attr(pb,'max_capacitance')
  if lim is not None:pinlimits[(typ,pn)]=Decimal(lim)
lines=['set_thread_count 8',f'read_liberty {{{LIB}}}',f'read_db {{{a.stage}/final.odb}}',f'read_sdc {{{a.stage}/final.sdc}}']
if sm['stage']=='drt':lines += [f'read_spef -coupling_reduction_factor 1.0 {{{a.stage}/route.spef}}']
else:lines += [f'source {{{P}/setRC.tcl}}',f'read_global_route_segments {{{a.stage}/route.segments}}','estimate_parasitics -global_routing']
for k in(1,10):
 for n,v in net['ports'].items():
  if v['direction']=='output':lines += [f'set_load {k} [get_ports {{{n}}}]']
 lines += [f'puts "BEGIN_CAP_LOAD{k}"','report_check_types -max_capacitance -max_count 100000 -digits 9',f'puts "END_CAP_LOAD{k}"']
s=a.out/'probe.tcl';s.write_text(tcl_script(lines));command(a.out,'probe',[OR,'-exit',s],300);log=(a.out/'probe.log').read_text();byload={}
for k in(1,10):
 part=block(log,'BEGIN_CAP_LOAD'+str(k),'END_CAP_LOAD'+str(k));rows=re.findall(r'(?m)^(\S+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+\((MET|VIOLATED)\)',part);need(0<len(rows)<100000,'complete finite cap report below requested ceiling');d={}
 for pin,lim,cap,slack,status in rows:
  need(pin not in d,'unique actual driver cap check');values=list(map(Decimal,(lim,cap,slack)));need(all(x.is_finite()for x in values)and values[0]>0 and values[1]>=0,'finite physical cap/limit');d[pin]={'limit':values[0],'cap':values[1],'slack':values[2]}
 byload[k]=d
need(set(byload[1])==set(byload[10]),'same checked pins both loads');records=[];clock_excluded=[];missing=[];expected=[]
for n,c in net['cells'].items():
 for pn,bs in c['connections'].items():
  if c['port_directions'][pn]!='output'or(c['type'],pn)not in pinlimits:continue
  need(len(bs)==1,'scalar driver');pin=n+'/'+pn;expected.append(pin)
  if pin not in byload[1]:
   if len(refs[bs[0]])>1:missing.append(pin)
   continue
  if canon(bs[0])[0]==clock:clock_excluded.append(pin);continue
  row=max((byload[k][pin]for k in(1,10)),key=lambda v:v['cap']/v['limit']);ll=pinlimits[(c['type'],pn)];need(abs(row['limit']-ll)<=max(Decimal('0.00001'),ll*Decimal('0.000001')),'actualSTA/Liberty limit float precision');records.append({'pin':pin,'master':c['type'],'cap_fF':str(row['cap']),'maxcap_fF':str(row['limit']),'ratio':str(row['cap']/row['limit']),'single_BUF_X4_can_drive_observed_load':row['cap']<Decimal('242.31'),'drives_top_ports':any(x.startswith('PORT:')for x in refs[bs[0]]),'sinks':len(refs[bs[0]])-1})
need(not missing,'all connected library-limited output pins appear in actual report: '+str(missing[:10]));area=sum((lib[c['type']]['area']for c in net['cells'].values()),Decimal(0));bud=Decimal('79600.5');bins=[]
for threshold in ('0.75','0.80','0.85','0.90'):
 selected=[x for x in records if Decimal(x['ratio'])>=Decimal(threshold)];unsupported=[x['pin']for x in selected if not x['single_BUF_X4_can_drive_observed_load']];extra=Decimal('1.862')*len(selected);bins.append({'threshold':threshold,'selected_count':len(selected),'selected_driver_pins':[x['pin']for x in selected],'unsupported_single_BUF_X4_drivers':unsupported,'additional_area_um2':str(extra),'new_cell_area_um2':str(area+extra),'budget_balance_um2':str(bud-area-extra),'within_area_budget':area+extra<=bud})
records.sort(key=lambda q:Decimal(q['ratio']),reverse=True);put(a.out/'distribution.json',{'status':'READONLY_ACTUAL_CAP_HEADROOM_DISTRIBUTION_NOT_REPAIR_AUTHORIZATION','source':sources(),'resources':resource_snapshot(),'stage_manifest_sha256':sha(a.stage/'manifest.json'),'stage_directory':str(a.stage),'RC_scope':'actual detailed OpenRCX SPEF readback'if sm['stage']=='drt'else'actual GRT in-memory estimate reproduced from original segments','base_area_um2':str(area),'budget_um2':str(bud),'all_reported_pins_per_load':len(byload[1]),'connected_driver_coverage_missing':missing,'clock_driver_excluded':clock_excluded,'internal_nonclock_checked_count':len(records),'thresholds':bins,'records':records,'limits':['Read-only quantities at current geometry; insertion/legalization/rerouting changes capacitance.','BUF feasibility uses current load only; proposed new net still needs actual all-constraint route and exact gate.','Includes internal cell drivers of top ports; excludes clock-equivalent driver cones, and primary-input drivers.']});manifest(a.out,{'status':'ACTUAL_CAP_DISTRIBUTION_EXECUTED_NOT_REPAIR','source':sources(),'stage_manifest_sha256':sha(a.stage/'manifest.json')});print('ACTUAL_CAP_DISTRIBUTION_EXECUTED_NOT_REPAIR')
