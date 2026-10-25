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

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--library',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False)
 rows=[];rs={};evidence=[]
 for kind,suffix,top in(('norm','01','block82'),('M','02','chain82')):
  for profile in range(3):
   for stall in range(2):
    tag=(''if kind=='norm'else'M-')+f'rtl-p{profile}s{stall}{suffix}';receipt=a.root/('receipt-'+tag+'.json');m=load(receipt);run=a.root/tag
    need(m['status']==('PASS_EXACT_INTEGER_FULL_ROW_RTL'if kind=='norm'else'PASS_REAL_M_COMPLETE_CONSUMER'),'independent actual receipt')
    need(m['profile']==profile and m['stall']==stall and m['run_manifest_sha256']==sha(run/'manifest.json'),'exact execution')
    rm=load(run/'manifest.json')
    for e in rm['artifacts']:need(sha(run/e['path'])==e['sha256'],'actual run artifact')
    need(m['negative']['status']=='REJECTED_AFTER_REHASH'and all(m['protocol'].values()),'independent actual negative/reset')
    actual=[load_line for load_line in map(json.loads,(run/'actual.jsonl').read_text().splitlines())]
    rs[kind,profile,stall]=actual
    evidence.append({'run':tag,'receipt_sha256':sha(receipt),'run_manifest_sha256':sha(run/'manifest.json')})
   mapping=a.root/(f'map-p{profile}01'if kind=='norm'else f'M-map-p{profile}03');r=resources(mapping,top,a.library)
   func=load(a.root/('receipt-'+(''if kind=='norm'else'M-')+f'rtl-p{profile}s0{suffix}'+'.json'))
   for n,d in func['source']['sources'].items():
    if n.startswith('project/rtl/')and n.endswith('.sv'):need(r['source']['sources'].get(n)==d,'mapped RTL exact functional source')
   r.update(kind=kind,profile=profile);rows.append(r)
 for kind in('norm','M'):
  reference=rs[kind,0,0]
  for p0 in range(3):
   for s in range(2):
    for x,y in zip(reference,rs[kind,p0,s]):
     need(x['name']==y['name']and x['status']==y['status']and x['out']==y['out'],'identical published numeric formats across resource/stall variants')
     if kind=='M':
      for key in('acc','down','joined','M_MACs','M_packets','M_store_lines','wire_beats','transactions'):need(x[key]==y[key],'same complete M function and physical IO '+key)
 metrics=[]
 for s in range(2):
  for kind in('norm','M'):
   values=[next(x for x in rs[kind,p,s]if x['name']=='L0T0')for p in range(3)]
   c=[x['cycles']for x in values];metrics.append({'kind':kind,'stall':s,'representative':'L0T0','cycles':c,'P2_vs_P0_cycle_reduction_percent':100*(c[0]-c[2])/c[0],'P2_vs_P0_equal_time_min_clock_ratio':c[2]/c[0],'P2_vs_P1_equal_time_min_clock_ratio':c[2]/c[1],'rows':[{k:v for k,v in x.items()if k not in('out','acc','down','joined')}for x in values]})
 result={'status':'PASS_SOURCE_FUNCTION_RESOURCE_AREA_COMPARISON','formal_norm_commands':84,'formal_M_commands':36,'resources':rows,'metrics':metrics,'evidence':evidence,'limits':['Only this finite full-K matrix consumer, not full model. Prior36 M commands retained as precursor, not extra distinct inputs.','Exact native wide add/sub/compare/shift and iterative SFU hardware are included even PROFILE0 is not byte-only hardware.','Same memory/precision/ports, different arithmetic area; no same-area claim or clock/STA/PPA qualification.','Entire common16KiB store82 wrapper excluded from logic-only mapping; actual memory bits and generic flops separate.','Standalone norm specialization does not replace the general18function V/ROM. Whole-system integration and arbitration costs remain to be validated.','M feed uses repeated A/W paired beats and fixed128bit serialization; packing CPU latency, real DMA/native model throughput and postroute timing are outside cycles.']}
 (a.out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'])
if __name__=='__main__':main()
