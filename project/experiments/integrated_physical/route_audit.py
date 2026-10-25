"""Independent exact incidence graph, RC coverage and global-route metal ledger."""
import collections,re
from decimal import Decimal
from common import *
from receive_physical import block,bracket_name

def incidence(net):
 refs=collections.defaultdict(set);directions={};meta={}
 for n,c in net['cells'].items():
  meta[n]={'type':c['type'],'parameters':c['parameters'],'port_directions':c['port_directions'],'widths':{p:len(bs)for p,bs in c['connections'].items()}}
  for p,bs in c['connections'].items():
   need(len(bs)==1,'all standard cell pins scalar');ref=n+':'+p;refs[bs[0]].add(ref);directions[ref]=('cell',c['port_directions'][p],c['type'])
 for n,p in net['ports'].items():
  for i,b in enumerate(p['bits']):ref='PORT:'+bracket_name(n,p,i);refs[b].add(ref);directions[ref]=('port',p['direction'],None)
 return refs,directions,meta

def same_wiring(before,after):
 a,ad,ac=incidence(before);b,bd,bc=incidence(after);need(ac==bc and ad==bd,'exact cells/types/functions/ports/pin directions and widths')
 need({frozenset(x)for x in a.values()}=={frozenset(x)for x in b.values()},'all actual electrical pin equivalence classes identical including clock')
 for n,p in before['ports'].items():need({k:v for k,v in p.items()if k!='bits'}=={k:v for k,v in after['ports'][n].items()if k!='bits'},'all port metadata')
 return {'status':'PASS_EXACT_CELLS_TYPES_AND_ALL_ELECTRICAL_PIN_CLASSES','cells':len(ac),'pins_ports':len(ad),'electrical_classes':len(a)}

def route_audit(stage,previous,net,lib,pure=True):
 from structure import signature_graph
 sm=artifacts(stage);artifacts(previous);need(sm['previous_manifest_sha256']==sha(previous/'manifest.json'),'route source stage binding');top='chain93'if 'chain93'in load(stage/'final.json')['modules']else'chain97'
 identical=same_wiring(load(previous/'final.json')['modules'][top],net)if pure else {'status':'TRANSFORMED_GRAPH_REQUIRES_OWN_GATE_AND_ORIGINAL_PIN_FUNCTION_CERTIFICATE'};identical['final_verilog_byte_identical']=sha(previous/'final.v')==sha(stage/'final.v');identical['earlier_stage_manifest_sha256']=sha(previous/'manifest.json');identical['earlier_final_verilog_sha256']=sha(previous/'final.v');identical['route_final_verilog_sha256']=sha(stage/'final.v')
 need(sm['automatic_repairs']is(not pure) and sm['PG_tap_fill_inserted']is False and sm['retiming']is False and sm['remove_buffers']is False,'no hidden modifications')
 refs,dirs,cells=incidence(net);lookup={ref:b for b,rs in refs.items()for ref in rs};canonical=signature_graph(net,lib);clock=canonical(net['ports']['clk']['bits'][0])[0]
 def named_bit(n):
  n=re.sub(r'\\(.)',r'\1',n)
  if n in net['netnames']:
   p=net['netnames'][n];need(len(p['bits'])==1,'scalar net label');return p['bits'][0]
  m=re.fullmatch(r'(.+)\[(\d+)\]',n);need(m and m[1]in net['netnames'],'known physical net '+n);p=net['netnames'][m[1]];i=int(m[2])-p.get('offset',0);need(0<=i<len(p['bits']),'net bit range');return p['bits'][i]
 text=(stage/'route.spef').read_text();need('*DESIGN "'+top+'"'in text,'SPEF exact top')
 for unit in ('*T_UNIT 1 NS','*C_UNIT 1 FF','*R_UNIT 1 KOHM'):need(text.count(unit)==1,'exact declared SPEF unit '+unit)
 expected={b for b,rs in refs.items()if len(rs)>1};seen=set();names={};cap=Decimal(0);res_count=0;cap_count=0
 for m in re.finditer(r'(?ms)^\*D_NET (\S+) (\S+)\n(.*?)^\*END\s*$',text):
  name,total,body=m.groups();b=named_bit(name);need(b not in seen and name not in names,'unique annotated electrical class');seen.add(b);names[name]=b;need(Decimal(total).is_finite()and Decimal(total)>=0,'finite nonnegative total cap');cap+=Decimal(total)
  con=body.split('*CONN\n',1)[1].split('*CAP\n',1)[0];found=set()
  for line in con.strip().splitlines():
   tok=line.split();need(tok[0]in('*I','*P')and len(tok)>=3,'complete SPEF connection record');ref=('PORT:'if tok[0]=='*P'else'')+tok[1];need(ref in lookup and lookup[ref]==b and ref not in found,'every SPEF pin exact class');found.add(ref);kind,direction,typ=dirs[ref];need(tok[2]==('I'if direction=='input'else'O'),'SPEF pin direction')
   if kind=='cell':need(tok[3:]==['*D',typ],'actual SPEF cell master')
  need(found==refs[b],'all pin/port RC coverage')
  cb=body.split('*CAP\n',1)[1].split('*RES\n',1)[0];rb=body.split('*RES\n',1)[1];nodes=set();graph=collections.defaultdict(set);rids=set();cids=set()
  for line in rb.strip().splitlines():
   t=line.split();need(len(t)==4 and t[0].isdigit()and t[0]not in rids and Decimal(t[3]).is_finite()and Decimal(t[3])>=0,'uniqueID finite nonnegative resistance');rids.add(t[0]);graph[t[1]].add(t[2]);graph[t[2]].add(t[1]);nodes|={t[1],t[2]};res_count+=1
  for line in cb.strip().splitlines():
   t=line.split();need(len(t)==3 and t[0].isdigit()and t[0]not in cids and Decimal(t[2]).is_finite()and Decimal(t[2])>=0,'uniqueID finite nonnegative ground capacitance');cids.add(t[0]);need(t[1]in nodes,'capacitor connected to RC graph');cap_count+=1
  cn={x.removeprefix('PORT:')for x in found};need(cn<=nodes,'all logical pins present in RC network');visited=set();todo=[next(iter(nodes))]
  while todo:
   q=todo.pop()
   if q not in visited:visited.add(q);todo.extend(graph[q]-visited)
  need(visited==nodes,'each complete parasitic RC network connected')
 need(seen==expected,'every multi-terminal electrical net has RC, no missing classes')
 log=(stage/'flow.log').read_text();rc=block(log,'BEGIN_GLOBAL_RC','END_GLOBAL_RC');un=re.search(r'Found (\d+) unannotated drivers\.\n(.*?)Found (\d+) partially unannotated drivers\.',rc,re.S);need(un is not None and int(un[3])==0,'explicit zero partial parasitic coverage');ul=[x.strip()for x in un[2].splitlines()if x.strip()];need(len(ul)==len(set(ul))==int(un[1]),'exact unannotated driver list');unbound=[]
 for pin in ul:
  inst,p=pin.rsplit('/',1);ref=inst+':'+p;need(ref in lookup and dirs[ref][0]=='cell'and dirs[ref][1]=='output'and refs[lookup[ref]]=={ref},'unannotated driver has no physical sink or port');unbound.append(pin)
 need({ref.replace(':','/')for b,rs in refs.items()if len(rs)==1 for ref in rs if dirs[ref][0]=='cell'and dirs[ref][1]=='output'}==set(ul),'all and only unused output drivers explicitly excluded')
 grid=re.findall(r'GCELLGRID ([XY]) 0 DO (\d+) STEP (\d+) ;',(stage/'placed.def').read_text());need(len(grid)==2 and {q[0]for q in grid}=={'X','Y'}and len({q[2]for q in grid})==1,'exact square actual global-route grid');tile=int(grid[0][2]);seg=(stage/'route.segments').read_text();wire={};metric={};by={k:collections.defaultdict(int)for k in('signal','clock')};via={k:collections.Counter()for k in('signal','clock')};segment_nets={};unit=2000
 for m in re.finditer(r'(?ms)^(\S+)\n\(\n(.*?)^\)\s*$',seg):
  n,body=m.groups();need(n in names and n not in wire,'route segment unique SPEF net');wire[n]=0;metric[n]=0;segment_nets[n]=names[n];kind='clock'if canonical(names[n])[0]==clock else'signal'
  for line in body.strip().splitlines():
   t=line.split();need(len(t)==6,'full route segment');x,y,l,x2,y2,l2=t;x,y,x2,y2=map(int,(x,y,x2,y2));need(all(0<=v<=896000 for v in(x,y,x2,y2)),'segment within fixed die');need(re.fullmatch(r'metal(?:[1-9]|10)',l)and re.fullmatch(r'metal(?:[1-9]|10)',l2),'known layer')
   if l==l2:
    need(x==x2 or y==y2,'Manhattan segment');length=abs(x-x2)+abs(y-y2);wire[n]+=length;metric[n]+=length+(tile if length else 0);by[kind][l]+=length
   else:
    need(x==x2 and y==y2 and abs(int(l[5:])-int(l2[5:]))==1,'adjacent zero-XY via');via[kind]['-'.join(sorted((l,l2),key=lambda q:int(q[5:])))]+=1
 need(segment_nets==names,'all SPEF nets present in actual global route segments')
 lines=(stage/'wirelength.csv').read_text().splitlines();need(lines[0].split()==['tool','net','total_wl','#pins'],'known actual net wirelength format');wn=set()
 for line in lines[1:]:
  t=line.split();need(len(t)==4 and t[0]=='grt:'and t[1]in names and t[1]not in wn,'exact wirelength net');wn.add(t[1]);need(abs(Decimal(t[2])-Decimal(metric[t[1]])/unit)<=Decimal('.005'),'independent per-net wirelength matches report precision');need(int(t[3])==len(refs[names[t[1]]]),'wirelength physical terminal count')
 need(wn==set(names),'complete wirelength net inventory');gr=block(log,'BEGIN_GLOBAL_ROUTE','END_GLOBAL_ROUTE');cong=gr.split('Final congestion report:',1)[1];layerrows=re.findall(r'(?m)^(metal\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+) /\s*(\d+) /\s*(\d+)\s*$',cong);need(len(layerrows)==10 and {q[0]for q in layerrows}=={'metal'+str(i)for i in range(1,11)}and all(int(x[4])==int(x[5])==int(x[6])==0 for x in layerrows),'all actual route layer overflows zero')
 return {'status':'PASS_EXACT_ROUTE_GRAPH_RC_COVERAGE_AND_LAYER_LEDGER','graph_identity':identical,'annotated_net_classes':len(seen),'RC_resistors':res_count,'RC_ground_caps':cap_count,'reported_net_total_cap_fF':str(cap),'unannotated_unused_driver_count':len(ul),'unannotated_unused_driver_names':unbound,'unexplained_unannotated':0,'partially_unannotated':0,'layer_wirelength_um':{k:{l:str(Decimal(v)/unit)for l,v in sorted(ls.items(),key=lambda q:int(q[0][5:]))}for k,ls in by.items()},'layer_vias':{k:dict(v)for k,v in via.items()},'congestion_layers':[{'layer':n,'resource':int(r),'demand':int(d),'reported_percent':pct,'H_overflow':int(h),'V_overflow':int(v),'total_overflow':int(t)}for n,r,d,pct,h,v,t in layerrows],'PG':'absent; no capacity reservation, power network or physical closure claim','pin_access':'Actual standard-cell pin access includes M1 vias and clock M2/M3 segments despite configured M4 minimum clock trunk; all are counted. No claim all clock metal is M4 or higher.','fixed_base_qualification':False,'global_route_tile_dbu':tile,'wirelength_metric_rule':'Installed GlobalRouter.cpp computeNetWirelength sums segment Manhattan length plus one grid tile for each positive planar segment. Physical planar length and tool metric remain separate; vias separately counted.','tool_metric_sum_um':str(sum(metric.values())/unit),'raw_planar_sum_um':str(sum(wire.values())/unit),'RC_scope':'global routing estimated RC, not detailed extracted parasitics'}
