"""Independent Liberty/graph certificate; no synthesis or timing-script reuse."""
import collections,copy,json,re
from decimal import Decimal

def need(v,s):
 if not v:raise ValueError(s)
def groups(text,kind):
 pattern=re.compile(r'\b'+re.escape(kind)+r'\s*\(\s*([^)]*)\)\s*\{')
 for m in pattern.finditer(text):
  i=m.end();depth=1;quoted=False;escape=False
  while depth and i<len(text):
   c=text[i]
   if escape:escape=False
   elif c=='\\':escape=True
   elif c=='"':quoted=not quoted
   elif not quoted:depth+=(c=='{')-(c=='}')
   i+=1
  need(depth==0,'balanced Liberty '+kind);yield m.group(1).strip().strip('"'),text[m.end():i-1]
def attr(body,key,default=None):
 m=re.search(r'(?m)^\s*'+re.escape(key)+r'\s*:\s*([^;]+);',body)
 return m.group(1).strip().strip('"')if m else default
def norm(s):return re.sub(r'\s+','',s or'')
def library(path):
 txt=re.sub(r'/\*.*?\*/','',path.read_text(),flags=re.S);txt=re.sub(r'//[^\n]*','',txt)
 need(attr(txt,'time_unit')=='1ns','Liberty time unit')
 cap=re.search(r'capacitive_load_unit\s*\(\s*1\s*,\s*ff\s*\)',txt,re.I);need(bool(cap),'Liberty fF unit')
 lib={}
 for name,body in groups(txt,'cell'):
  pins={}
  for n,p in groups(body,'pin'):
   vals={k:attr(p,k)for k in('capacitance','rise_capacitance','fall_capacitance')}
   pins[n]={'direction':attr(p,'direction'),'function':norm(attr(p,'function')),'cap':{k:Decimal(v)for k,v in vals.items()if v is not None}}
  seq={k:[(n,norm(b))for n,b in groups(body,k)]for k in('ff','latch')}
  inp=[n for n,p in pins.items()if p['direction']=='input'];out=[n for n,p in pins.items()if p['direction']=='output'];trans=None
  if len(out)==1 and not any(seq.values()):
   f=pins[out[0]]['function']
   if not inp and f in('0','1'):trans=('tie',int(f),out[0])
   elif len(inp)==1 and f in(inp[0],'!'+inp[0],inp[0]+"'"):trans=('wire',inp[0],out[0],int(f!=inp[0]))
  lib[name]={'area':Decimal(attr(body,'area')),'pins':pins,'sequential':seq,'transparent':trans,'logic':({n:(p['direction'],p['function'])for n,p in pins.items()},seq)}
 return lib

def signature_graph(net,lib):
 drivers={};memo={};active=set()
 def add(bit,value):
  need(not isinstance(bit,str),'driven literal prohibited');need(bit not in drivers,'multiple drivers');drivers[bit]=value
 for name,p in net['ports'].items():
  if p['direction']=='input':
   for i,b in enumerate(p['bits']):add(b,('port',name,i))
 for name,c in net['cells'].items():
  need(c['type']in lib,'unknown cell '+c['type']);lp=lib[c['type']]['pins']
  need(set(c['connections'])==set(lp),'exact library pin set')
  for pin,bits in c['connections'].items():
   need(len(bits)==1 and c['port_directions'][pin]==lp[pin]['direction'],'scalar pin direction/width')
   if lp[pin]['direction']=='output':add(bits[0],('cell',name,pin,0))
 def canon(bit):
  if isinstance(bit,str):need(bit in('0','1'),'undefined bit');return(('constant',int(bit)),0)
  if bit in memo:return memo[bit]
  need(bit not in active,'combinational buffer loop');need(bit in drivers,'undriven bit');active.add(bit);d=drivers[bit]
  if d[0]=='cell':
   c=net['cells'][d[1]];t=lib[c['type']]['transparent']
   if t and t[0]=='tie':result=(('constant',t[1]),0)
   elif t:
    term,inv=canon(c['connections'][t[1]][0]);inv^=t[3]
    result=((('constant',term[1]^inv),0)if term[0]=='constant'else(term,inv))
   else:result=(d,0)
  else:result=(d,0)
  active.remove(bit);memo[bit]=result;return result
 # Check every referenced bit, including otherwise unobserved original buffer trees.
 for c in net['cells'].values():
  for bits in c['connections'].values():
   for bit in bits:canon(bit)
 for p in net['ports'].values():
  for bit in p['bits']:canon(bit)
 return canon

def certificate(before,after,lib):
 need(set(before['ports'])==set(after['ports']),'all original ports retained')
 for n,p in before['ports'].items():
  q=after['ports'][n];need(p['direction']==q['direction']and len(p['bits'])==len(q['bits']),'port width/direction '+n)
 need(set(before['cells'])<=set(after['cells']),'original cells retained')
 added=set(after['cells'])-set(before['cells'])
 for n in added:need(lib[after['cells'][n]['type']]['transparent']is not None,'no new logic/sequential cell')
 bcanon=signature_graph(before,lib);acanon=signature_graph(after,lib);pins=0;changed=[]
 for n,c in before['cells'].items():
  d=after['cells'][n];need(lib[c['type']]['logic']==lib[d['type']]['logic'],'same cell Boolean and sequential function '+n)
  need(c['parameters']==d['parameters']and c['port_directions']==d['port_directions'],'cell parameters/pin set')
  if c['type']!=d['type']:changed.append({'cell':n,'before':c['type'],'after':d['type']})
  for pin,bs in c['connections'].items():
   ds=d['connections'][pin];need(len(bs)==len(ds),'cell pin width')
   for x,y in zip(bs,ds):need(bcanon(x)==acanon(y),'cell pin function '+n+'/'+pin);pins+=1
 const=[];portbits=0
 for n,p in before['ports'].items():
  for i,(x,y)in enumerate(zip(p['bits'],after['ports'][n]['bits'])):
   need(bcanon(x)==acanon(y),'top/cut port bit function '+n+'/'+str(i));portbits+=1
   if p['direction']=='output'and bcanon(x)[0][0]=='constant':const.append({'port':n,'bit':i,'value':bcanon(x)[0][1]})
 hist0=collections.Counter(c['type']for c in before['cells'].values());hist1=collections.Counter(c['type']for c in after['cells'].values())
 area0=sum((lib[n]['area']*count for n,count in hist0.items()),Decimal(0));area1=sum((lib[n]['area']*count for n,count in hist1.items()),Decimal(0));need(area1<=Decimal(80000),'shared cell area budget')
 dffs=[n for n,c in before['cells'].items()if any(lib[c['type']]['sequential'].values())]
 return {'status':'PASS_ALL_ORIGINAL_PIN_AND_PORT_FUNCTIONS_AFTER_TRANSPARENT_FOLD','original_cells':len(before['cells']),'final_cells':len(after['cells']),'original_pin_bits_checked':pins,'port_bits_checked':portbits,'sequential_cells_preserved_with_all_pins':len(dffs),'constant_output_bits':const,'resized':changed,'added_histogram':dict(collections.Counter(after['cells'][n]['type']for n in added)),'before_histogram':dict(hist0),'after_histogram':dict(hist1),'before_area_um2':str(area0),'after_area_um2':str(area1),'added_area_um2':str(area1-area0),'area_limit_um2':'80000'}

def input_loads(net,lib):
 sinks=collections.defaultdict(list);outputs=collections.Counter()
 for name,c in net['cells'].items():
  for pin,bits in c['connections'].items():
   if c['port_directions'][pin]=='input':
    for bit in bits:sinks[bit].append((name,pin,c['type']))
 for p in net['ports'].values():
  if p['direction']=='output':outputs.update(p['bits'])
 rows=[]
 for n,p in net['ports'].items():
  if p['direction']!='input':continue
  for i,bit in enumerate(p['bits']):
   nominal=Decimal(0);conservative=Decimal(0);buffers=0
   for _,pin,cell in sinks[bit]:
    cap=lib[cell]['pins'][pin]['cap'];need(cap,'input capacitance defined '+cell+'/'+pin)
    nominal+=cap.get('capacitance',max(cap.values()));conservative+=max(cap.values());buffers+=int(lib[cell]['transparent']is not None)
   rows.append({'port':n,'bit':i,'direct_sink_pins':len(sinks[bit]),'first_level_transparent_cells':buffers,'nominal_pin_cap_fF':str(nominal),'max_rise_fall_pin_cap_fF':str(conservative),'aliased_external_output_loads':outputs[bit],'clock_ideal':n=='clk','upstream_driver_impedance_modeled':False})
 return rows