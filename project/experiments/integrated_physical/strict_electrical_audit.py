"""Independent reception of exact full unfiltered electrical tables."""
import re,sys
from decimal import Decimal
from common import *
from receive_physical import block
from route_audit import incidence
sys.path.insert(0,str(ROOT/'project/experiments/electrical_repair'))
from structure import groups,attr
def slew_coverage(stage,log):
 """Exact scope for this frozen library/SDC, not a general Liberty interpreter."""
 text=re.sub(r'/\*.*?\*/','',LIB.read_text(),flags=re.S);text=re.sub(r'//[^\n]*','',text);sdc=(stage/'final.sdc').read_text()
 need(attr(text,'time_unit')=='1ns','slew library time unit ns');defaults=re.findall(r'(?m)^\s*default_max_transition\s*:\s*([^;]+);',text)
 need(len(defaults)==1 and not re.search(r'(?m)^\s*max_transition\s*:',text),'one library default and no unsupported per-pin transition override');limit=Decimal(defaults[0]);need(limit.is_finite()and limit>0,'finite positive library slew bound')
 need(not re.search(r'(?m)^\s*(?:set_max_transition|set_driving_cell|set_drive|set_ideal_network|set_ideal_latency|set_ideal_transition)\b',sdc),'frozen SDC has no additional driver/ideal/transition rule requiring separate coverage')
 libs={}
 for master,body in groups(text,'cell'):libs[master]={pin:attr(pb,'direction')for pin,pb in groups(body,'pin')}
 mods=load(stage/'final.json')['modules'];net=mods[next(x for x in mods if x in('chain93','chain97'))];refs,_,_=incidence(net);expected=set();connected=set()
 for name,c in net['cells'].items():
  need(c['type']in libs and set(c['connections'])==set(libs[c['type']]),'all library pins present in exact final netlist')
  for pn,bs in c['connections'].items():
   need(len(bs)==1 and c['port_directions'][pn]==libs[c['type']][pn],'scalar library pin direction')
   if c['port_directions'][pn]=='output':
    pin=name+'/'+pn;expected.add(pin)
    if len(refs[bs[0]])>1:connected.add(pin)
 for k in(1,10):
  section=block(log,f'BEGIN_FULL_max_slew_{k}',f'END_FULL_max_slew_{k}');rows=re.findall(r'(?m)^(\S+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+\((MET|VIOLATED)\)',section);table={r[0]:r for r in rows}
  need(len(table)==len(rows)and set(table)==expected,'complete exact slew driver set including unused/tie/clock outputs, load '+str(k))
  for row in rows:need(abs(Decimal(row[1])-limit)<=max(Decimal('0.00000001'),limit*Decimal('0.0000001')),'actual slew limit bound to library, float reporting precision only')
 encoded=('\n'.join(sorted(expected))+'\n').encode();inputs=sum(len(p['bits'])for p in net['ports'].values()if p['direction']=='input')
 return {'status':'PASS_EXACT_ALL_LIBRARY_OUTPUT_DRIVER_SLEW_COVERAGE','expected_output_pins':len(expected),'connected_output_pins':len(connected),'unused_output_pins':len(expected-connected),'driver_set_sha256':__import__('hashlib').sha256(encoded).hexdigest(),'default_max_transition_ns':str(limit),'library_sha256':sha(LIB),'sdc_sha256':sha(stage/'final.sdc'),'netlist_sha256':sha(stage/'final.json'),'top_input_bits_without_applicable_driver_slew_limit':inputs,'scope':'Frozen library default applies to cell output drivers including tie, unused and propagated clock outputs. No set_max_transition or driving-cell rule for ideal top-level source ports; their waveform is fixed, upstream driver closure is not claimed.'}

def parse_full(stage,log):
 slew_coverage(stage,log)
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
 actual=parse_full(stage,(directory/'probe.log').read_text());need(r['scenarios']==actual,'every full electrical count/row binds actual report');closed=all(c['strict_count']==0 for x in actual for c in x['checks'].values());need(type(r['all_electrical_maxima_met'])is bool and r['all_electrical_maxima_met']==closed,'typed strict closure result');return {'status':'PASS_FULL_REPORT_MAXIMA_AND_EXACT_SLEW_CONNECTED_CAP_DRIVER_COVERAGE','all_electrical_maxima_met':closed,'scenarios':actual,'slew_coverage':slew_coverage(stage,(directory/'probe.log').read_text()),'receipt_sha256':sha(directory/'receipt.json'),'manifest_sha256':sha(directory/'manifest.json')}
