import pathlib,json
P=pathlib.Path;p=P(__file__).resolve().parent
tech='/public/home/yuzelu/PingyangHuang/issue-199-rcx-w4JD5wxq/job-98197/patterns/overlay/research12.tech.lef'
rules='/public/home/yuzelu/PingyangHuang/issue-199-rcx-w4JD5wxq/job-98197/fit/research12.rules'
paths={'A':'/public/home/yuzelu/project-circuit/issue287-route-ab-20261117/A-mapped.json','B':'/public/home/yuzelu/project-circuit/side-top-pressure-20261117/route-fixed.json'}
for label,path in paths.items():
 routes=json.loads(P(path).read_text())['routes'];out=p/('rcx-'+label);out.mkdir(exist_ok=True);pins=[];nets=[]
 for i,(name,r) in enumerate(sorted(routes.items())):
  connections=[]
  for k,v in enumerate(r['via10']):
   pin='p%d_%d'%(i,k);x,y=v['at'];connections.append('( PIN %s )'%pin)
   pins.append('- %s + NET %s + DIRECTION %s + USE SIGNAL\n + PORT + LAYER metal10 ( -2000 -2000 ) ( 2000 2000 ) + FIXED ( %d %d ) N ;'%(pin,name,'INPUT' if k==0 else 'OUTPUT',x,y))
  wire=[]
  for s in r['segments']:
   if s['a']==s['b']:continue
   wire.append('%s ( %d %d ) ( %d %d )'%('metal'+s['layer'][1:],*s['a'],*s['b']))
  for v in r['via10']:wire.append('metal10 ( %d %d ) BV1_via10'%tuple(v['at']))
  for v in r['via11']:wire.append('metal11 ( %d %d ) BV1_via11'%tuple(v))
  nets.append('- '+name+' '+' '.join(connections)+' + USE SIGNAL\n + ROUTED '+'\n NEW '.join(wire)+' ;')
 text='VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\nDESIGN route_'+label+' ;\nUNITS DISTANCE MICRONS 2000 ;\nDIEAREA ( 0 0 ) ( 20000000 16000000 ) ;\nPINS '+str(len(pins))+' ;\n'+'\n'.join(pins)+'\nEND PINS\nNETS '+str(len(nets))+' ;\n'+'\n'.join(nets)+'\nEND NETS\nEND DESIGN\n'
 (out/'route.def').write_text(text)
 (out/'run.tcl').write_text('read_lef {'+tech+'}\nread_def route.def\nset_extraction_rules_file {'+rules+'}\ndefine_process_corner -ext_model_index 0 research\nextract_parasitics -context_depth 3 -coupling_threshold 0.000001 -max_res 0 -no_merge_via_res\nwrite_spef extracted.spef\nset f [open totals.tsv w]\nforeach n [[ord::get_db_block] getNets] {puts $f "[$n getName]\\t[$n getTotalResistance]"}\nclose $f\nputs RCX_COMPLETE\n')
