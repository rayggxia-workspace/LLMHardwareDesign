"""Independent exact graph, DEF geometry/connectivity and full endpoint reception."""
import argparse,collections,copy,csv,re,sys
from decimal import Decimal
from common import *
from admission93 import admit,MAP
from canonical import canonical_cut
from constraints_audit import audit_sdc
sys.path.insert(0,str(ROOT/'project/experiments/electrical_repair'))
from structure import library,certificate,input_loads
from physical_structure import certify_physical

def bracket_name(n,p,i):return n if len(p['bits'])==1 else n+'['+str(p.get('offset',0)+i)+']'
def rows(p):return list(csv.DictReader(p.read_text().splitlines(),delimiter='\t'))
def block(text,a,b):
 if a.startswith('BEGIN_'):
  aa=list(re.finditer(r'(?m)^'+re.escape(a)+r'[ \t]*$',text));bb=list(re.finditer(r'(?m)^'+re.escape(b)+r'[ \t]*$',text));need(len(aa)==len(bb)==1 and aa[0].end()<bb[0].start(),'unique ordered execution markers '+a);return text[aa[0].end():bb[0].start()]
 need(text.count(a)==text.count(b)==1,'unique section '+a);return text.split(a)[1].split(b)[0]
def lef_sizes(text):
 out={}
 for match in re.finditer(r'(?m)^MACRO\s+(\S+)',text):
  n=match.group(1);tail=text[match.end():];end=re.search(r'(?m)^END\s+'+re.escape(n)+r'\s*$',tail);need(end is not None,'complete LEF macro');m=re.search(r'SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)',tail[:end.start()]);need(m is not None,'LEF dimensions');out[n]=tuple(map(Decimal,m.groups()))
 return out

def def_name(n):return re.sub(r'\\(.)',r'\1',n)
def geometry_connectivity(text,net,lib,original=None):
 u=re.search(r'UNITS DISTANCE MICRONS (\d+)\s*;',text);need(u is not None,'DEF units');unit=int(u.group(1));num=lambda x:int(Decimal(x)*unit)
 core=tuple(map(num,['24.51','25.2','423.51','424.2']));die=re.search(r'DIEAREA\s*\(\s*(\d+)\s+(\d+)\s*\)\s*\(\s*(\d+)\s+(\d+)\s*\)',text);need(die is not None and tuple(map(int,die.groups()))==(0,0,num('448'),num('448')),'frozen die')
 rr=re.findall(r'ROW\s+\S+\s+(\S+)\s+(-?\d+)\s+(-?\d+)\s+(\S+)\s+DO\s+(\d+)\s+BY\s+(\d+)\s+STEP\s+(\d+)\s+(\d+)\s*;',text);need(len(rr)==285,'exact285 legal rows')
 for site,x,y,orient,nx,ny,dx,dy in rr:need(site=='FreePDK45_38x28_10R_NP_162NW_34O'and int(x)==core[0]and int(nx)==2100 and int(ny)==1 and int(dx)==num('.19')and int(dy)==0 and orient in('N','FS'),'frozen site/row capacity')
 ys={int(r[2])for r in rr};need(ys==set(range(core[1],core[3],num('1.4'))),'exact core Y rows')
 comp=block(text,'COMPONENTS ','END COMPONENTS');head=comp.split(';',1);count=int(head[0].strip());entries=re.findall(r'(?s)-\s+(\S+)\s+(\S+)\s+(.*?);',head[1]);need(len(entries)==count==len(net['cells']),'all DEF and gate cells')
 sizes=lef_sizes(LEF.read_text());occ=collections.defaultdict(list);insts={};area=Decimal(0)
 for rawname,master,rest in entries:
  name=def_name(rawname);need(name in net['cells']and name not in insts and net['cells'][name]['type']==master,'exact mapped cell/master in DEF');m=re.search(r'\+\s+(PLACED|FIXED)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\S+)',rest);need(m is not None,'placed instance');state,x,y,orient=m.groups();x=int(x);y=int(y);w,h=sizes[master];need(w*h==lib[master]['area'],'LEF/Liberty area');area+=w*h;wd=num(w);hd=num(h)
  need(orient in('N','FS','S','FN')and y in ys and(x-core[0])%num('.19')==0 and hd%num('1.4')==0,'site aligned standard cell');need(x>=core[0]and x+wd<=core[2]and y+hd<=core[3],'inside core')
  for yy in range(y,y+hd,num('1.4')):need(yy in ys,'height in legal rows');occ[yy].append((x,x+wd,name))
  insts[name]=(master,x,y,orient)
 for ys0,intervals in occ.items():
  intervals.sort()
  for left,right in zip(intervals,intervals[1:]):need(left[1]<=right[0],'independent row overlap')
 # Independently match every DEF signal connection to final gate bit identity.
 def bit(n,table):
  n=def_name(n)
  if n in table:need(len(table[n]['bits'])==1,'scalar named net');return table[n]['bits'][0]
  m=re.fullmatch(r'(.+)\[(\d+)\]',n);need(m is not None and m.group(1)in table,'named bit '+n);p=table[m.group(1)];i=int(m.group(2))-p.get('offset',0);need(0<=i<len(p['bits']),'busbit range');return p['bits'][i]
 nets=block(text,'\nNETS ','END NETS');parts=nets.split(';',1);nr=re.findall(r'(?s)-\s+(\S+)\s+(.*?);',parts[1]);need(len(nr)==int(parts[0].strip()),'DEF net count');seen=set();netbits={};bitnets={};empty_reference_nets=[]
 for n,body in nr:
  bb=None;conn=body.split('+',1)[0]
  for owner,pin in re.findall(r'\(\s*(\S+)\s+(\S+)\s*\)',conn):
   owner=def_name(owner);pin=def_name(pin)
   if owner=='PIN':key=('port',pin);actual=bit(pin,net['ports'])
   else:
    need(owner in net['cells']and pin in net['cells'][owner]['connections'],'known DEF instance pin');bs=net['cells'][owner]['connections'][pin];need(len(bs)==1,'scalar DEF cellpin');actual=bs[0];key=('cell',owner,pin)
   if bb is None:bb=actual
   need(key not in seen and bb==actual,'DEF pin connectivity equal exact netlist');seen.add(key)
  if bb is None:
   use=re.fullmatch(r'\s*\+ USE (GROUND|SIGNAL)\s*',body);need(use is not None,'empty DEF label has no routing or other physical objects')
   if use[1]=='GROUND':need(def_name(n)=='zero_','explicit empty ground reference')
   else:bit(n,(original or net)['netnames'])
   empty_reference_nets.append({'name':def_name(n),'use':use[1],'connections':0,'scope':'empty reference/alias label only; all actual cell and port connections remain required'});continue
  need(bb not in bitnets and def_name(n)not in netbits,'all electrical netlist bit classes not split '+n);netbits[def_name(n)]=bb;bitnets[bb]=def_name(n)
 expected={('cell',n,p)for n,c in net['cells'].items()for p,b in c['connections'].items()if b}|{('port',bracket_name(n,p,i))for n,p in net['ports'].items()for i in range(len(p['bits']))}
 need(seen==expected,'all cell and IO DEF connection coverage')
 # Pin metal rectangles, all boundary sites and two-track spacing are independent of renamed internal net labels.
 pp=block(text,'\nPINS ','END PINS');ph=pp.split(';',1);pins=re.findall(r'(?s)-\s+(\S+)\s+(.*?);',ph[1]);port_lookup={bracket_name(n,p,i):(p['direction'],p['bits'][i])for n,p in net['ports'].items()for i in range(len(p['bits']))};need(len(pins)==int(ph[0].strip())==len(port_lookup),'all physical port bits');pinmap={};edge_positions=collections.defaultdict(list);tracks={}
 for axis,start,count,step,layer in re.findall(r'TRACKS\s+([XY])\s+(\d+)\s+DO\s+(\d+)\s+STEP\s+(\d+)\s+LAYER\s+(metal[56])\s*;',text):tracks[(layer,axis)]=tuple(map(int,(start,count,step)))
 for rawname,body in pins:
  name=def_name(rawname);need(name in port_lookup and name not in pinmap,'unique physical pin');nn=re.search(r'\+ NET (\S+)',body);direction=re.search(r'\+ DIRECTION (INPUT|OUTPUT)',body);ls=re.findall(r'\+ LAYER (\S+) \(\s*(-?\d+) (-?\d+) \) \(\s*(-?\d+) (-?\d+) \)',body);pos=re.search(r'\+ (PLACED|FIXED) \(\s*(\d+) (\d+) \) (\S+)',body)
  need(nn and direction and len(ls)==1 and pos and body.count('+ PORT')==1,'exact physical pin rectangle and placement');need(direction[1].lower()==port_lookup[name][0]and netbits[def_name(nn[1])]==port_lookup[name][1],'DEF pin direction and net class');layer,x1,y1,x2,y2=ls[0];x1,y1,x2,y2=map(int,(x1,y1,x2,y2));x,y=int(pos[2]),int(pos[3]);need(pos[4]=='N'and layer in('metal5','metal6'),'frozen M5/M6 pin orientation');rect=(x+x1,y+y1,x+x2,y+y2);need(0<=rect[0]<rect[2]<=num('448')and 0<=rect[1]<rect[3]<=num('448'),'pin rectangle inside die')
  if layer=='metal5':need(rect[0]==0 or rect[2]==num('448'),'M5 left/right boundary');edge='left'if rect[0]==0 else'right';coordinate=y;axis='Y'
  else:need(rect[1]==0 or rect[3]==num('448'),'M6 bottom/top boundary');edge='bottom'if rect[1]==0 else'top';coordinate=x;axis='X'
  start,count,step=tracks[(layer,axis)];need((coordinate-start)%step==0 and 0<=(coordinate-start)//step<count,'pin on actual routing track');edge_positions[(layer,edge)].append(coordinate);pinmap[name]={'layer':layer,'direction':direction[1],'rectangle_dbu':list(rect),'position_dbu':[x,y],'edge':edge}
 for (layer,edge),coords in edge_positions.items():
  coords.sort();step=tracks[(layer,'Y'if layer=='metal5'else'X')][2];need(all(b-a>=2*step for a,b in zip(coords,coords[1:])),'same layer edge two-track pin spacing')
 need(set(pinmap)==set(port_lookup),'every port physical geometry');need(area<=Decimal('79600.5'),'frozen cell budget')
 return {'status':'PASS_INDEPENDENT_SITE_BOUNDS_NO_OVERLAP_AND_ALL_SIGNAL_CONNECTIONS','core_um2':'159201','legal_rows':285,'row_site_count':598500,'functional_clock_repair_area_um2':str(area),'functional_area_budget_um2':'79600.5','DEF_database_units_per_um':unit,'signal_pin_connections':len(seen),'signal_net_equivalence_classes':len(netbits),'empty_non_electrical_reference_nets':empty_reference_nets,'pin_geometry':pinmap,'pin_edge_counts':{layer+'/'+edge:len(coords)for(layer,edge),coords in edge_positions.items()},'physical_only_cells_inserted':0,'PG_tap_fill_and_real_macro':'not inserted in initial logic-island placement; no manufacturing legality claim'}

def audit(folder,prepared,out,gate=None,postgate=None):
 fm=artifacts(folder);pm=artifacts(prepared);ad=admit();need(pm['status']=='EXACT_ACCEPTED93_GATE_EXPORT_AND_DECLARED_MEMORY_CUT'and pm['admission_sha256']==sha(prepared/'admission.json')and load(prepared/'admission.json')==ad and fm['admission']==ad,'independent exact upstream admission');need(fm['stage']in('zero','place','repair','cts','ctsrepair')and fm['status']=='ACTUAL93_'+fm['stage'].upper()+'_EXECUTED_NOT_RECEIVED','actual stage complete');need(fm['prepared_manifest_sha256']==sha(prepared/'manifest.json'),'precise stage input')
 need(fm['config_sha256']==sha(HERE/'config.json'),'frozen physical config')
 for p in(LIB,TECH,LEF,P/'setRC.tcl',P/'make_tracks.tcl',P/'fastroute.tcl'):need(fm['views'][str(p)]==sha(p),'exact physical input view')
 lib=library(LIB);before=load(prepared/'cut-source.json')['modules']['chain93'];original=copy.deepcopy(load(MAP/'mapped.json')['modules']['chain93']);stores=[(n,c)for n,c in original['cells'].items()if c['type']=='store82'];need(len(stores)==1,'original single store');sn,sc=stores[0];del original['cells'][sn]
 for pn,bs in sc['connections'].items():
  if pn!='clk':original['ports']['store_'+pn]={'direction':'input'if sc['port_directions'][pn]=='output'else'output','bits':bs}
 need(original==before,'independent original mapped source cut all cells ports and nets');before=canonical_cut(prepared,out/'canonical');after=load(folder/'final.json')['modules']['chain93'];cert=certify_physical(before,after,lib);need(Decimal(cert['after_area_um2'])<=Decimal('79600.5'),'98 cell budget');
 if fm['stage']in('zero','place'):need(cert['added_histogram']=={}and cert['resized']==[],'no implicit buffer/resize in baseline')
 need(Decimal(str(load(folder/'stat.json')['design']['area']))==Decimal(cert['after_area_um2']),'independent exact library area')
 sdc=audit_sdc((folder/'final.sdc').read_text(),after['ports'],fm['stage']in('cts','ctsrepair'))
 ff={n+'/D'for n,c in after['cells'].items()if any(lib[c['type']]['sequential'].values())};outs={bracket_name(n,p,i)for n,p in after['ports'].items()if p['direction']=='output'for i in range(len(p['bits']))};exclude={bracket_name(e['port'],after['ports'][e['port']],e['bit'])for e in cert['constant_output_bits']};expected=ff|(outs-exclude)
 log=(folder/'flow.log').read_text();need(log.count('FLOW_EXECUTION_COMPLETE')==1,'actual tool completion marker');scenarios=[]
 for k in (1,10):
  logk=block(log,'BEGIN_SCENARIO_'+str(k),'END_SCENARIO_'+str(k));check=block(logk,'BEGIN_CHECK_SETUP','END_CHECK_SETUP');need(check.strip()=='','no unexplained unconstrained/no-clock endpoints');er=block(logk,'BEGIN_ELECTRICAL_REPORT','END_ELECTRICAL_REPORT');block(logk,'BEGIN_UNCONSTRAINED','END_UNCONSTRAINED')
  need('Error:'not in logk and'Warning:'not in logk,'scenario tool warning/error')
  by={n:rows(folder/f'{n}-load{k}.tsv')for n in('r2r','setup','hold')}
  for n,es in [('r2r',ff),('setup',expected),('hold',expected)]:names=[r['endpoint']for r in by[n]];need(len(names)==len(set(names))and set(names)==es,'complete exact '+n+' endpoint set')
  violations={}
  for n in('max slew','max capacitance','max fanout'):
   m=re.search(r'(?m)^'+n+r'\s*$',er);tail=er[m.end():]if m else'';end=re.search(r'(?m)^(max slew|max capacitance|max fanout|max delay/setup|min delay/hold)\s*$',tail);tail=tail[:end.start()]if end else tail;violations[n]=tail.count('(VIOLATED)')
  violations.update(setup=sum(Decimal(r['slack'])<0 for r in by['setup']),hold=sum(Decimal(r['slack'])<0 for r in by['hold']))
  scenarios.append({'load_fF':k,'violations':violations,'R2R_endpoints':len(ff),'all_setup_hold_endpoints':len(expected),'constant_output_exclusions':sorted(exclude),'unexplained_unconstrained':0,'fanout_scope':'Only explicitly present Liberty/SDC limits; no invented target maximum. Actual per-input fanout reported separately.','worst_setup_ns':str(min(Decimal(r['slack'])for r in by['setup'])),'worst_hold_ns':str(min(Decimal(r['slack'])for r in by['hold'])),'closed':not any(violations.values())})
 geo=None;gate_status='NOT_REQUIRED_ZERO_DIAGNOSTIC';gate_sha=None;post_status='NOT_EXECUTED';post_sha=None
 if fm['stage']in('place','repair','cts','ctsrepair'):
  gate_status='PENDING_RAW_GATE_PROVISIONAL_ONLY'
  if gate is not None:
   gr=load(gate/'receipt.json');need(gr['status']=='PASS_ACTUAL93_COMPLETE_GATES_AND_DECLARED_EPOCH_EXCEPTION'and gr['admission']==ad and gr['prepared_manifest_sha256']==sha(prepared/'manifest.json'),'independent same exact complete raw gate');gate_status='PASS_COMPLETE_RAW_GATE';gate_sha=sha(gate/'receipt.json')
 if fm['stage']in('place','repair','cts','ctsrepair'):block(log,'BEGIN_CHECK_PLACEMENT','END_CHECK_PLACEMENT');geo=geometry_connectivity((folder/'placed.def').read_text(),after,lib,before)
 if postgate is not None:
  pg=load(postgate/'receipt.json');need(pg['status']=='PASS_POSTPHYSICAL93_COMPLETE_GATES_AND_DECLARED_EPOCH_EXCEPTION'and pg['admission']==ad and pg['prepared_manifest_sha256']==sha(prepared/'manifest.json')and pg['postphysical']['physical_stage_manifest_sha256']==sha(folder/'manifest.json')and pg['postphysical']['physical_final_verilog_sha256']==sha(folder/'final.v'),'complete gate replay of this actual physical netlist');post_status='PASS_COMPLETE_POSTPHYSICAL_GATE';post_sha=sha(postgate/'receipt.json')
 if fm['stage']in('repair','cts','ctsrepair'):
  prev=Path(fm['previous_directory']);need(fm['previous_manifest_sha256']==sha(prev/'manifest.json'),'preceding actual physical stage binding');old_geo=geometry_connectivity((prev/'placed.def').read_text(),load(prev/'final.json')['modules']['chain93'],lib,before);need(old_geo['pin_geometry']==geo['pin_geometry'],'exact frozen external pinmap through physical transformations')
 return {'stage':fm['stage'],'stage_manifest_sha256':sha(folder/'manifest.json'),'structure':cert,'actual_constraints':sdc,'input_sink_costs':input_loads(after,lib),'scenarios':scenarios,'physical_geometry':geo,'all_declared_internal_timing_electrical_closed':all(s['closed']for s in scenarios),'postphysical_gate_status':post_status,'postphysical_gate_receipt_sha256':post_sha,'raw_gate_status':gate_status,'gate_receipt_sha256':gate_sha,'physical_stage_accepted':fm['stage']in('place','repair','cts','ctsrepair')and gate_status=='PASS_COMPLETE_RAW_GATE'and post_status=='PASS_COMPLETE_POSTPHYSICAL_GATE'and all(s['closed']for s in scenarios),'macro_clock_load_qualified':False,'upstream_drive_qualified':False,'manufacturable':False}

def main():
 p=argparse.ArgumentParser();p.add_argument('--prepared',type=Path,required=True);p.add_argument('--stage',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--gate',type=Path);p.add_argument('--postgate',type=Path);a=p.parse_args();a.out.mkdir(exist_ok=False);bd=sources();r=audit(a.stage,a.prepared,a.out,a.gate,a.postgate)
 put(a.out/'receipt.json',{'schema':'physical98-receipt-v1','status':'PASS_RECEPTION_OF_EXECUTED_PHYSICAL_STAGE_NOT_AUTOMATIC_CLOSURE','source':bd,'result':r,'limits':['Research Nangate typical only; explicitly non-manufacturable.','Whole store82 cut excludes real SRAM timing/area and macro clock load; core_reset retained at store_reset output.','Placement is logic island without PG/tap/fill or actual macro; zero wire/placement estimates are not detailed route SPEF.']});print('PASS_RECEPTION_OF_EXECUTED_PHYSICAL_STAGE_NOT_AUTOMATIC_CLOSURE')
if __name__=='__main__':main()
