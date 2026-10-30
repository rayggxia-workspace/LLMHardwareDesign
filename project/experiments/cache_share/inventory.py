"""Independent artifact, functional-equality and mapped-area/resource comparison."""
import argparse,json,hashlib,re
from pathlib import Path
from collections import Counter
from decimal import Decimal

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def need(v,s):
 if not v:raise ValueError(s)
def num(v):return int(v,2)if isinstance(v,str)else v

def resources(folder,top,library):
 m=load(folder/'manifest.json');need(m['status']=='LOGIC_ONLY_MAPPED_NOT_PPA','actual map finished')
 for e in m['artifacts']:need(sha(folder/e['path'])==e['sha256'],'actual mapping artifact')
 need(m['library_sha256']==sha(library),'exact shared library')
 mods=load(folder/'generic.json')['modules'];types=Counter();mem=[];ff=0;mul=[]
 def walk(name):
  nonlocal ff
  for c in mods[name]['cells'].values():
   t=c['type'];p=c['parameters']
   if t in mods:walk(t);continue
   types[t]+=1;need(t not in('$div','$mod','$pow'),'no hidden native division')
   if 'dff'in t.lower():ff+=num(p['WIDTH'])
   if t=='$mul':mul.append({k:num(p[k])for k in('A_WIDTH','B_WIDTH','Y_WIDTH','A_SIGNED','B_SIGNED')})
   if t=='$mem_v2':mem.append({k:num(p[k])for k in('WIDTH','SIZE','RD_PORTS','WR_PORTS')})
 walk(top);need(mem==[{'WIDTH':128,'SIZE':1024,'RD_PORTS':1,'WR_PORTS':1}],'exact one shared16KiB frame')
 actual=Counter(c['type']for c in load(folder/'mapped.json')['modules'][top]['cells'].values());stat=load(folder/'stat.json')['design'];need(dict(actual)==stat['num_cells_by_type'],'native stat equals actual instances')
 need(actual.pop('store82')==1,'one unmapped common storage wrapper');annotations=actual.pop('$scopeinfo',0);need(not any(x.startswith('$')for x in actual),'all other hardware mapped')
 areas={};cell=None
 for line in library.read_text().splitlines():
  line=line.strip()
  if line.startswith('cell ('):cell=line.split('(',1)[1].split(')',1)[0].strip(' "')
  elif line.startswith('area')and':'in line and cell:areas[cell]=Decimal(line.split(':',1)[1].split(';',1)[0].strip())
 area=sum(areas[t]*n for t,n in actual.items());need(abs(area-Decimal(str(stat['area'])))<Decimal('0.00001'),'independent original-library area sum')
 return {'area_um2_logic_only':float(area),'mapped_cells':sum(actual.values()),'DFF_X1':actual.get('DFF_X1',0),'generic_register_bits_including_frame_wrapper':ff,'memory_cells':mem,'memory_bits':131072,'multipliers':mul,'source':m['source'],'manifest_sha256':sha(folder/'manifest.json'),'scope_annotations':annotations}
