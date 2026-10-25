"""Read-only actual clock geometry drift and all-endpoint hold target exposure."""
import argparse,re,csv,sys,collections
from decimal import Decimal,ROUND_CEILING
from common import *
from receive_physical import library,block,def_name
from route_audit import incidence
sys.path.insert(0,str(ROOT/'project/experiments/electrical_repair'))
from structure import signature_graph
p=argparse.ArgumentParser();p.add_argument('--target',type=int,choices=[93,97],required=True);p.add_argument('--before',type=Path,required=True);p.add_argument('--after',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);lib=library(LIB);runs=[]
for stage in(a.before,a.after):
 artifacts(stage);net=load(stage/'final.json')['modules']['chain'+str(a.target)];canon=signature_graph(net,lib);clock=canon(net['ports']['clk']['bits'][0])[0];refs,_,_=incidence(net);names={n for n,v in net['netnames'].items()if len(v['bits'])==1 and v['bits'][0]in refs and canon(v['bits'][0])[0]==clock};cells={n for n,c in net['cells'].items()if any(c['port_directions'][pn]=='output'and canon(bs[0])[0]==clock for pn,bs in c['connections'].items())};text=(stage/'placed.def').read_text();loc={def_name(n):(typ,x,y,orient)for n,typ,x,y,orient in re.findall(r'(?s)-\s+(\S+)\s+(\S+)\s+.*?\+ (?:PLACED|FIXED) \(\s*(\d+) (\d+) \) (\S+)',block(text,'COMPONENTS ','END COMPONENTS').split(';',1)[1])};segs={}
 for m in re.finditer(r'(?ms)^(\S+)\n\(\n(.*?)^\)\s*$',(stage/'route.segments').read_text()):
  n=re.sub(r'\\(.)',r'\1',m[1])
  if n in names:segs[n]=sorted(x.strip()for x in m[2].strip().splitlines())
 runs.append({'clock_cells':cells,'locations':{n:loc[n]for n in cells},'clock_segments':segs})
b,c=runs;need(b['clock_cells']==c['clock_cells']and set(b['clock_segments'])==set(c['clock_segments']),'same exact clock cell/net set');changed=[n for n in b['clock_segments']if b['clock_segments'][n]!=c['clock_segments'][n]];moved=[{'cell':n,'before':b['locations'][n],'after':c['locations'][n]}for n in b['clock_cells']if b['locations'][n]!=c['locations'][n]];rows=list(csv.DictReader((a.after/'hold-load10.tsv').read_text().splitlines(),delimiter='\t'));cohorts={}
for margin in('0','.02','.05'):
 selected=[x for x in rows if Decimal(x['slack'])<Decimal(margin)];need25=sum((int(((Decimal(margin)-Decimal(x['slack']))/Decimal('.025')).to_integral_value(rounding=ROUND_CEILING))for x in selected),0);cohorts[margin]={'endpoints':len(selected),'example_no_sharing_25ps_buffers':need25,'illustrative_area_um2':str(lib['CLKBUF_X1']['area']*need25)}
put(a.out/'comparison.json',{'status':'READONLY_CLOCK_GEOMETRY_AND_HOLD_TARGET_COHORT','source':sources(),'before_manifest_sha256':sha(a.before/'manifest.json'),'after_manifest_sha256':sha(a.after/'manifest.json'),'clock_cells':len(b['clock_cells']),'clock_route_nets':len(b['clock_segments']),'changed_clock_segment_nets':changed,'moved_clock_cells':moved,'hold_target_cohorts':cohorts,'CLKBUF_X1_area_um2':str(lib['CLKBUF_X1']['area']),'limits':['25ps illustrative buffer delay uses observed small-load timing, not a guaranteed physical minimum or precise optimizer prediction.','Target50ps applies all below-target endpoints, including currently legal ones; sharing can change inserted count.','No new repair executed.']});print('READONLY_CLOCK_GEOMETRY_AND_HOLD_TARGET_COHORT')
