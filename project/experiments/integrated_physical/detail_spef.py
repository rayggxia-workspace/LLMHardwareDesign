"""Independent RCX NAME_MAP, units, all-pin connectivity and cap conservation."""
import collections,re
from decimal import Decimal
from common import *
from route_audit import incidence
from receive_physical import block

def number(s):
 v=Decimal(s);need(v.is_finite()and v>=0,'finite nonnegative extracted R/C');return v

def round6(v):return Decimal(0)if v==0 else Decimal('0.5')*Decimal(10)**(v.adjusted()-5)

def audit_spef(stage,net):
 refs,dirs,cells=incidence(net);lookup={r:b for b,rs in refs.items()for r in rs};text=(stage/'route.spef').read_text();top='chain93'if 'chain93'in load(stage/'final.json')['modules']else'chain97';need('*DESIGN "'+top+'"'in text,'exact extracted top')
 for u in ('*T_UNIT 1 NS','*C_UNIT 1 PF','*R_UNIT 1 OHM'):need(text.count(u)==1,'actual RCX declared unit '+u)
 prefix=text.split('*NAME_MAP\n',1)[1].split('*PORTS',1)[0].split('*D_NET',1)[0];names={}
 for line in prefix.strip().splitlines():
  if not line.strip():continue
  m=re.fullmatch(r'\*(\d+) (.+)',line);need(m and m[1]not in names,'unique complete RCX name map');names[m[1]]=re.sub(r'\\(.)',r'\1',m[2])
 def resolve(s):
  if not s.startswith('*'):return re.sub(r'\\(.)',r'\1',s)
  m=re.fullmatch(r'\*(\d+)(:.*)?',s);need(m and m[1]in names,'defined name-map reference');return names[m[1]]+(m[2]or'')
 def bit(n):
  if n in net['netnames']:
   p=net['netnames'][n];need(len(p['bits'])==1,'scalar extracted net');return p['bits'][0]
  m=re.fullmatch(r'(.+)\[(\d+)\]',n);need(m and m[1]in net['netnames'],'known extracted busbit '+n);p=net['netnames'][m[1]];i=int(m[2])-p.get('offset',0);need(0<=i<len(p['bits']),'extracted bit range');return p['bits'][i]
 expected={b for b,rs in refs.items()if len(rs)>1};seen=set();global_nodes={};coupling=collections.defaultdict(lambda:collections.defaultdict(Decimal));pending=[];totals=[];R=0;Cg=0;Cc=0
 for m in re.finditer(r'(?ms)^\*D_NET (\S+) (\S+)\n(.*?)^\*END\s*$',text):
  raw,total,body=m.groups();name=resolve(raw);b=bit(name);need(b not in seen,'unique extracted net class');seen.add(b);total=number(total);con=body.split('*CONN\n',1)[1].split('*CAP\n',1)[0];found=set();nodepins=set()
  for line in con.strip().splitlines():
   t=line.split();need(len(t)>=3 and t[0]in('*I','*P'),'full extracted connection');node=resolve(t[1]);ref=('PORT:'if t[0]=='*P'else'')+node;need(ref in lookup and lookup[ref]==b and ref not in found,'exact extracted cellpin/port class');found.add(ref);nodepins.add(node);kind,direction,typ=dirs[ref];need(t[2]==('I'if direction=='input'else'O'),'extracted direction')
   if kind=='cell':need(t[3:]==['*D',typ],'extracted actual cell master')
  need(found==refs[b],'every actual electrical pin covered in extracted CONN');rb=body.split('*RES\n',1)[1];graph=collections.defaultdict(set);ids=set()
  for line in rb.strip().splitlines():
   t=line.split();need(len(t)==4 and t[0].isdigit()and t[0]not in ids,'unique extracted resistor id');ids.add(t[0]);x,y=resolve(t[1]),resolve(t[2]);number(t[3]);graph[x].add(y);graph[y].add(x);R+=1
  nodes=set(graph);need(nodepins<=nodes,'all extracted terminals in resistor graph');visited=set();todo=[next(iter(nodes))]
  while todo:
   x=todo.pop()
   if x not in visited:visited.add(x);todo.extend(graph[x]-visited)
  need(visited==nodes,'complete conductive RC graph connected')
  for node in nodes:need(node not in global_nodes,'extracted node belongs to one electrical net');global_nodes[node]=b
  cb=body.split('*CAP\n',1)[1].split('*RES\n',1)[0];ids=set();values=[]
  for line in cb.strip().splitlines():
   t=line.split();need(len(t)in(3,4)and t[0].isdigit()and t[0]not in ids,'unique complete extracted capacitor id');ids.add(t[0]);v=number(t[-1]);values.append(v);x=resolve(t[1])
   if len(t)==3:need(x in nodes,'ground capacitor attached to own conductive net');Cg+=1
   else:
    y=resolve(t[2]);need(x in nodes or y in nodes,'coupling attached to own net');pending.append((x,y,b));coupling[tuple(sorted((x,y)))][b]+=v;Cc+=1
  value=sum(values,Decimal(0));tolerance=round6(total)+sum((round6(v)for v in values),Decimal(0));need(abs(total-value)<=tolerance,'actual ground+coupling D_NET conservation within six-significant-digit writer rounding '+name);totals.append({'net':name,'total_pf':str(total),'sum_pf':str(value),'difference_pf':str(total-value),'rounding_bound_pf':str(tolerance)})
 need(seen==expected,'every multi-terminal class extracted, none omitted')
 for x,y,b in pending:need(x in global_nodes and y in global_nodes and b in(global_nodes[x],global_nodes[y]),'coupling endpoints resolve to actual conductive networks')
 for pair,values in coupling.items():
  owners={global_nodes[x]for x in pair};need(set(values)==owners,'both sides of each actual symmetric coupling capacitor')
  if len(owners)==2:need(len(set(values.values()))==1,'mirrored coupling values exactly equal after same writer rounding')
 log=(stage/'flow.log').read_text();section=block(log,'BEGIN_DETAILED_RCX','END_DETAILED_RCX');m=re.search(r'Found (\d+) unannotated drivers\.\n(.*?)Found (\d+) partially unannotated drivers\.',section,re.S);need(m and int(m[3])==0,'explicit zero partial extraction coverage');ul=[x.strip()for x in m[2].splitlines()if x.strip()];need(len(ul)==len(set(ul))==int(m[1]),'exact extracted unannotated count')
 for pin in ul:
  n,p=pin.rsplit('/',1);ref=n+':'+p;need(ref in lookup and dirs[ref][0]=='cell'and dirs[ref][1]=='output'and refs[lookup[ref]]=={ref},'every extraction exclusion is unused singleton output')
 need({r.replace(':','/')for b,rs in refs.items()if len(rs)==1 for r in rs if dirs[r][0]=='cell'and dirs[r][1]=='output'}==set(ul),'all and only excluded unused drivers')
 return {'status':'PASS_FULL_EXTRACTED_PIN_RC_CONNECTIVITY_AND_GROUND_COUPLING_CONSERVATION','annotated_net_classes':len(seen),'resistors':R,'ground_cap_records':Cg,'coupling_records':Cc,'unique_coupling_pairs':len(coupling),'total_D_NET_fF':str(sum((Decimal(x['total_pf'])for x in totals),Decimal(0))*1000),'unannotated_unused_driver_count':len(ul),'unexplained_unannotated':0,'partially_unannotated':0,'writer_precision':'exact installed extSpef.cpp printf %g default6 significant digits; each net tolerance is sum of half-last-digit bounds, no physical margin','net_conservation':totals,'scope':'Research RCX rule model and conservative coupling reduction1, not independent electromagnetic solution or manufacturing extraction qualification.'}
