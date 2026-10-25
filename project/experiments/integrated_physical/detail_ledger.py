"""Strict all-net DEF routed centerline/via ledger, separate from RC solver."""
import collections,re,sys
from decimal import Decimal
from common import *
from receive_physical import block,library
from route_audit import incidence
sys.path.insert(0,str(ROOT/'project/experiments/electrical_repair'))
from structure import signature_graph

def audit_ledger(stage,net):
 text=(stage/'placed.def').read_text();ndr=block(text,'NONDEFAULTRULES 1 ;','END NONDEFAULTRULES');need(re.fullmatch(r'\s*- CTS_NDR_0\s+(?:\+ LAYER metal(?:[1-9]|10) WIDTH \d+ SPACING \d+\s+){10};\s*',ndr),'exact complete clock NDR declaration');ndr_rows=re.findall(r'LAYER (metal\d+) WIDTH (\d+) SPACING (\d+)',ndr);ndr_nets=[];need(re.search(r'^UNITS DISTANCE MICRONS 2000 ;$',text,re.M),'actual fixed DEF units');need(not re.search(r'^(SPECIALNETS|VIAS) ',text,re.M),'no hidden special nets or generated vias in this frozen flow')
 tech=TECH.read_text();vias={}
 for m in re.finditer(r'(?ms)^VIA (\S+)(?: DEFAULT)?\s*\n(.*?)^END \1\s*$',tech):
  layers=re.findall(r'\bLAYER (\S+) ;',m[2]);metals=sorted((x for x in layers if re.fullmatch(r'metal(?:[1-9]|10)',x)),key=lambda x:int(x[5:]));need(len(layers)==3 and len(metals)==2 and int(metals[1][5:])-int(metals[0][5:])==1,'complete adjacent technology via');vias[m[1]]=metals
 need(vias,'actual technology via definitions');refs,dirs,cells=incidence(net);lookup={r:b for b,rs in refs.items()for r in rs};canon=signature_graph(net,library(LIB));clock=canon(net['ports']['clk']['bits'][0])[0]
 mm=re.search(r'(?ms)^NETS (\d+) ;\n(.*?)^END NETS\s*$',text);need(mm,'one complete routed NETS section');body=mm[2];records=re.findall(r'(?ms)^\s*- (\S+) (.*?);',body);need(len(records)==int(mm[1]),'all physical DEF net records accounted');need(not re.sub(r'(?ms)^\s*- (\S+) (.*?);','',body).strip(),'no unparsed DEF net material');seen=set();wire={k:collections.Counter()for k in('signal','clock')};via={k:collections.Counter()for k in('signal','clock')};by_master=collections.Counter();routes=collections.Counter();unused=[];empty=[];zero_extensions=0
 for name,entry in records:
  # DEF native escaped names use the same actual port/cell spelling after unescape.
  parts=entry.split('+',2);need(len(parts)>=2,'every net declares USE');connect=parts[0];use=parts[1].strip();need(use in('USE SIGNAL','USE CLOCK','USE GROUND','USE POWER'),'known net use');pins=re.findall(r'\( (\S+) (\S+) \)',connect);need(not re.sub(r'\( (\S+) (\S+) \)','',connect).strip(),'complete connection grammar');found=set()
  for cell,pin in pins:
   cell=re.sub(r'\\(.)',r'\1',cell);pin=re.sub(r'\\(.)',r'\1',pin);ref=('PORT:'+pin)if cell=='PIN'else(cell+':'+pin);need(ref in lookup and ref not in found,'exact routed net pin/port');found.add(ref)
  if not found:
   need(len(parts)==2 and use in('USE GROUND','USE POWER'),'only empty unrouted power metadata');empty.append({'net':name,'use':use});continue
  bs={lookup[x]for x in found};need(len(bs)==1,'one electrical class per DEF net');b=next(iter(bs));need(found==refs[b]and b not in seen,'complete unique DEF electrical class');seen.add(b);kind='clock'if canon(b)[0]==clock else'signal';need(use not in('USE POWER','USE GROUND'),'no actual PG network silently classified as signal')
  if len(parts)==2:need(len(found)==1,'unrouted class only unused single driver');unused.append(name);continue
  route=parts[2].strip()
  if route.startswith('NONDEFAULTRULE '):
   need(kind=='clock'and route.startswith('NONDEFAULTRULE CTS_NDR_0\n'),'exact declared clock NDR only');route=route.split('+',1)[1].strip();ndr_nets.append(name)
  need(route.startswith('ROUTED '),'only actual regular ROUTED geometry');segments=re.split(r'\s+NEW\s+',route.removeprefix('ROUTED '));routes[kind]+=1
  for seg in segments:
   tokens=re.findall(r'\(|\)|[^\s()]+',seg);need(tokens and re.fullmatch(r'metal(?:[1-9]|10)',tokens[0]),'actual routing layer');layer=tokens[0];i=1;last=None
   if i<len(tokens)and tokens[i]=='TAPER':i+=1
   while i<len(tokens):
    if tokens[i]=='(':
     j=i+1
     while j<len(tokens)and tokens[j]!=')':j+=1
     need(j<len(tokens)and j-i in(3,4),'exact XY with optional zero end extension');raw=tokens[i+1:i+3];xy=[]
     if j-i==4:need(tokens[i+3]=='0','only actual zero end extension, no uncounted geometry');zero_extensions+=1
     for axis,v in enumerate(raw):
      if v=='*':need(last is not None,'relative coordinate after initial point');xy.append(last[axis])
      else:need(re.fullmatch(r'-?\d+',v),'integer routed coordinate');xy.append(int(v))
     need(all(0<=v<=896000 for v in xy),'every routed coordinate within frozen die')
     if last is not None:need(last[0]==xy[0]or last[1]==xy[1],'Manhattan detailed wire');wire[kind][layer]+=abs(last[0]-xy[0])+abs(last[1]-xy[1])
     last=xy;i=j+1
    else:
     v=tokens[i];need(last is not None and v in vias,'known real via record, reject unparsed routing feature '+v);need(layer in vias[v],'via touches current physical layer');via[kind]['-'.join(vias[v])]+=1;by_master[v]+=1;layer=next(x for x in vias[v]if x!=layer);i+=1
 need(seen==set(refs),'all actual electrical classes represented by full DEF')
 log=(stage/'flow.log').read_text();dr=block(log,'BEGIN_DETAILED_ROUTE','END_DETAILED_ROUTE');counts=re.findall(r'(?m)^.*(?:Number of vias|Total number of vias)\s*[:=]\s*(\d+)',dr)
 return {'status':'PASS_FULL_DEF_PIN_CLASSES_ROUTING_GRAMMAR_AND_LAYER_LEDGER','net_records':len(records),'clock_NDR_nets':ndr_nets,'clock_NDR_layers_dbu':[{'layer':l,'width':int(w),'spacing':int(sp)}for l,w,sp in ndr_rows],'electrical_classes':len(seen),'routed_nets':dict(routes),'unrouted_singletons':len(unused),'empty_metadata_nets':empty,'wirelength_um':{k:{'metal'+str(i):str(Decimal(d['metal'+str(i)])/2000)for i in range(1,11)}for k,d in wire.items()},'via_layer_pairs':{k:dict(d)for k,d in via.items()},'via_masters':dict(by_master),'total_vias':sum(by_master.values()),'explicit_zero_end_extensions':zero_extensions,'total_centerline_um':str(sum(sum(v.values())for v in wire.values())/Decimal(2000)),'PG':'absent; no supply routing, tap/fill, power integrity or manufacturing qualification','measurement':'Actual DEF centerline Manhattan lengths; via rectangles/enclosures separate and not added to wire length; no independent electromagnetic RC solution.'}

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);artifacts(a.stage);mods=load(a.stage/'final.json')['modules'];net=mods[next(x for x in mods if x in('chain93','chain97'))];put(a.out/'receipt.json',audit_ledger(a.stage,net));print('PASS_FULL_DEF_LAYER_LEDGER')
