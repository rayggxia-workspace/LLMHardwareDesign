"""Independent reception of exact full unfiltered electrical tables."""
import re,sys
from decimal import Decimal
from common import *
from receive_physical import block
from route_audit import incidence
sys.path.insert(0,str(ROOT/'project/experiments/electrical_repair'))
from structure import groups,attr
def parse_full(stage,log):
 scenarios=[]
 for k in(1,10):
  checks={}
  for check in('max_slew','max_capacitance','max_fanout'):
   section=block(log,f'BEGIN_FULL_{check}_{k}',f'END_FULL_{check}_{k}');rows=re.findall(r'(?m)^(\S+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+\((MET|VIOLATED)\)',section);need(len(rows)<1000000,'full report below maximum count');seen=set();bad=[]
   for pin,lim,actual,slack,status in rows:
    need(pin not in seen,'unique full-check pin');seen.add(pin);v=list(map(Decimal,(lim,actual,slack)));need(all(x.is_finite()for x in v)and v[0]>0 and v[1]>=0,'finite full-check quantities');
    if v[1]>v[0]:bad.append({'pin':pin,'limit':lim,'actual':actual,'slack':slack,'native_row_status':status})
   if check!='max_fanout':need(len(rows)>0,'nonempty complete maxslew/maxcap report')
   else:need(rows or((not section.strip()or'No paths found.'in section)and not re.search(r'\b(?:default_)?max_fanout\b',LIB.read_text())and'set_max_fanout'not in(stage/'final.sdc').read_text()),'empty report only with no actual fanout limit in bound Liberty/SDC')
   checks[check]={'checked_pins':len(rows),'strict_exceedances':bad,'strict_count':len(bad),'report_sha256':__import__('hashlib').sha256(section.encode()).hexdigest()}
  scenarios.append({'load_fF':k,'checks':checks})
 for check in('max_slew','max_capacitance','max_fanout'):need(scenarios[0]['checks'][check]['checked_pins']==scenarios[1]['checks'][check]['checked_pins'],'same full check coverage both loads')
 mods=load(stage/'final.json')['modules'];net=mods[next(x for x in mods if x in('chain93','chain97'))];refs,dirs,cells=incidence(net);limits={}
 for master,body in groups(LIB.read_text(),'cell'):
  for pin,pb in groups(body,'pin'):
   lim=attr(pb,'max_capacitance')
   if lim is not None:limits[(master,pin)]=Decimal(lim)
 for k in(1,10):
  sec=block(log,f'BEGIN_FULL_max_capacitance_{k}',f'END_FULL_max_capacitance_{k}');rows=re.findall(r'(?m)^(\S+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+\((MET|VIOLATED)\)',sec);table={x[0]:x for x in rows}
  for n,c in net['cells'].items():
   for pn,bs in c['connections'].items():
    if c['port_directions'][pn]!='output'or(c['type'],pn)not in limits:continue
    need(len(bs)==1,'scalar capped output');pin=n+'/'+pn
    if len(refs[bs[0]])>1:need(pin in table,'complete connected driver cap coverage '+pin)
    if pin in table:
     got=Decimal(table[pin][1]);lim=limits[(c['type'],pn)];need(abs(got-lim)<=max(Decimal('0.00001'),lim*Decimal('0.000001')),'actual full cap report/Liberty bound float precision')
 return scenarios

def receive_strict(stage,directory):
 sm=artifacts(stage);m=artifacts(directory);r=load(directory/'receipt.json');need(m['status']=='COMPLETE_ELECTRICAL_REPORT_CHECKS_EXECUTED'and m['stage_directory']==str(stage)and m['stage_manifest_sha256']==sha(stage/'manifest.json'),'exact independent electrical stage binding');need(r['stage_directory']==str(stage)and r['stage_manifest_sha256']==sha(stage/'manifest.json')and r['source']==m['source'],'full electrical receipt source binding');need(m['library_sha256']==sha(LIB),'same exact library')
 for n in('final.odb','final.sdc','final.json'):need(m['inputs'][n]==sha(stage/n),'exact electrical readback input '+n)
 actual=parse_full(stage,(directory/'probe.log').read_text());need(r['scenarios']==actual,'every full electrical count/row binds actual report');closed=all(c['strict_count']==0 for x in actual for c in x['checks'].values());need(type(r['all_electrical_maxima_met'])is bool and r['all_electrical_maxima_met']==closed,'typed strict closure result');return {'status':'PASS_FULL_REPORT_MAXIMA_AND_CONNECTED_CAP_DRIVER_COVERAGE','all_electrical_maxima_met':closed,'scenarios':actual,'receipt_sha256':sha(directory/'receipt.json'),'manifest_sha256':sha(directory/'manifest.json')}
