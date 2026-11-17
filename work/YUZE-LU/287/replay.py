"""Real routed RC replay on accepted C/U native netlists; quiet aggressors."""
import pathlib,re,json,csv,hashlib,collections,subprocess,concurrent.futures,os
P=pathlib.Path
ROOT=P(__file__).resolve().parent
SPEF=P('/public/home/yuzelu/PingyangHuang/issue-215-top-pex-paPJkRpL/job-99183/result/field.spef')
GEO=P('/public/home/yuzelu/PingyangHuang/issue-204-qwen-switch-r19/channel-verify-98674/odb-check/wire-rectangles.tsv')
def sha(p):return hashlib.sha256(P(p).read_bytes()).hexdigest()
def prepare():
 cfg=json.loads((ROOT/'inputs.json').read_text())
 # Route-box length excludes end caps: Manhattan centerline estimate, DBU=2000.
 lengths=collections.defaultdict(float);names={}
 for line in GEO.open():
  if line.startswith('# NET'):
   _,_,key,h=line.split();names[key]=bytes.fromhex(h).decode()
  elif not line.startswith('#'):
   key,layer,kind,*xy=line.split()
   if kind=='wire':
    x0,y0,x1,y1=map(int,xy);lengths[names[key]]+=(max(x1-x0,y1-y0)-min(x1-x0,y1-y0))/2000
 # Parse metadata once without retaining the entire coupled network in memory.
 maps={};stats={};mode=None;net=None
 for line in SPEF.open():
  a=line.split()
  if not a:continue
  if a[0]=='*NAME_MAP':mode='map';continue
  if a[0]=='*D_NET':
   net=maps[a[1]];stats[net]={'name':net,'length_um':lengths[net],'total_pf':float(a[2]),'R_sum_ohm':0.0};mode='net'
  elif a[0]=='*RES':mode='R'
  elif a[0]=='*END':mode=None
  elif a[0].startswith('*') and mode=='map' and a[0][1:].isdigit():maps[a[0]]=a[1]
  elif mode=='R' and a[0].isdigit():stats[net]['R_sum_ohm']+=float(a[-1])
 ordered=sorted(stats.values(),key=lambda x:x['length_um'])
 selected={}
 for label,q in [('p10',.10),('p50',.5),('p90',.9),('longest',1)]:selected[label]=ordered[round((len(ordered)-1)*q)]['name']
 selected['maxC']=max(stats,key=lambda n:stats[n]['total_pf'])
 selected['maxR']=max(stats,key=lambda n:stats[n]['R_sum_ohm'])
 wanted=set(selected.values());sections={};lines=None
 for line in SPEF.open():
  a=line.split()
  if a and a[0]=='*D_NET':
   net=maps[a[1]];lines=[] if net in wanted else None
  if lines is not None:lines.append(line)
  if a and a[0]=='*END' and lines is not None:sections[net]=''.join(lines);lines=None
 def resolve(s):
  m=re.match(r'(\*\d+)(.*)',s)
  return maps[m[1]]+m[2] if m else s
 # Couplers are stored ONCE, sometimes in the other net's section.
 node_owner={}
 for net,section in sections.items():
  mode=None
  for line in section.splitlines():
   a=line.split()
   if not a:continue
   if a[0]=='*RES':mode='R';continue
   if a[0]=='*END':mode=None
   if mode=='R' and a[0].isdigit():
    for n in a[1:3]:node_owner[resolve(n)]=net
 allcaps={n:collections.defaultdict(float) for n in wanted};totals={n:[0.,0.] for n in wanted}
 mode=None
 for line in SPEF.open():
  a=line.split()
  if not a:continue
  if a[0]=='*CAP':mode='C';continue
  if a[0] in ('*RES','*END','*D_NET'):mode=None
  if mode=='C' and a[0].isdigit():
   for token in a[1:-1]:
    node=resolve(token)
    if node in node_owner:
     n=node_owner[node];val=float(a[-1]);allcaps[n][node]+=val;totals[n][len(a)-3]+=val
 # Netlist harness keeps the actual output drivers and receiving cells.
 decl=['input clk'];inst=[]
 for role in ('C','U'):
  v=(ROOT/(role+'-v2')/'exported.v').read_text();top=re.search(r'module\s+(\S+)\s*\(',v)[1]
  con=[]
  for direction,width,name in re.findall(r'^\s*(input|output|inout)\s*(\[[^\]]+\])?\s*(\\\S+|\w+)\s*;',v,re.M):
   if name=='clk_i':expr='clk'
   elif (role,name) in [('C','outgoing_data'),('U','incoming_data')]:expr='link_data'
   else:
    assert not name.startswith('\\'),name
    expr=role+'_'+name;decl.append(f'{direction} {width} {expr}')
   con.append(f'.{name}({expr})')
  inst.append(f'{top} {role} (\n'+',\n'.join(con)+'\n);')
 (ROOT/'harness.v').write_text('module cu_replay(\n'+',\n'.join(decl)+'\n);\nwire [127:0] link_data;\n'+'\n'.join(inst)+'\nendmodule\n')
 head='*SPEF "IEEE 1481-1998"\n*DESIGN "cu_replay"\n*DATE "2026-11-17"\n*VENDOR "research"\n*PROGRAM "issue287"\n*VERSION "1"\n*DESIGN_FLOW "NAME_SCOPE LOCAL" "PIN_CAP NONE"\n*DIVIDER /\n*DELIMITER :\n*BUS_DELIMITER []\n*T_UNIT 1 NS\n*C_UNIT 1 PF\n*R_UNIT 1 OHM\n*L_UNIT 1 HENRY\n'
 samples={'ideal':None,**selected};audit={}
 for label,net in samples.items():
  caps=collections.defaultdict(float);res=[];ends={};cg=cc=0.
  if net:
   mode=None
   for line in sections[net].splitlines():
    a=line.split()
    if not a:continue
    if a[0] in ('*CONN','*CAP','*RES'):mode=a[0];continue
    if mode=='*CONN' and a[0]=='*I':ends[resolve(a[1])]=a[2]
    elif mode=='*CAP' and a[0].isdigit():
     value=float(a[-1]);nodes=[resolve(x) for x in a[1:-1]]
     local=[x for x in nodes if x.startswith(net+':') or x in ends]
     assert len(local)==1,(net,nodes)
     caps[local[0]]+=value
     if len(nodes)==1:cg+=value
     else:cc+=value
    elif mode=='*RES' and a[0].isdigit():res.append((resolve(a[1]),resolve(a[2]),a[3]))
   caps=allcaps[net];cg,cc=totals[net]
   assert sorted(ends.values())==['I','O']
   assert abs(sum(caps.values())-stats[net]['total_pf'])<1e-6,(net,cg,cc,stats[net]['total_pf'])
  text=head
  for bit in range(128):
   src=f'C:outgoing_data[{bit}]';dst=f'U:incoming_data[{bit}]';nn=f'link_data[{bit}]'
   def node(x):
    if x in ends:return src if ends[x]=='O' else dst
    assert x.startswith(net+':');return nn+':'+x.split(':',1)[1]
   text+=f'\n*D_NET {nn} {sum(caps.values()):.14g}\n*CONN\n*I {src} O\n*I {dst} I\n*CAP\n'
   for i,(n,v) in enumerate(caps.items(),1):text+=f'{i} {node(n)} {v:.14g}\n'
   text+='*RES\n'
   if net:
    for i,(a,b,v) in enumerate(res,1):text+=f'{i} {node(a)} {node(b)} {v}\n'
   else:text+=f'1 {src} {dst} 0\n'
   text+='*END\n'
  (ROOT/(label+'.spef')).write_text(text)
  audit[label]={'source':net,'Cg_pf':cg,'Cc_pf':cc,'R_edges':len(res),'sha256':sha(ROOT/(label+'.spef')),**(stats[net] if net else {})}
 (ROOT/'samples.json').write_text(json.dumps(audit,indent=2))
 (ROOT/'distribution.json').write_text(json.dumps({'count':len(ordered),'length_method':'sum wire-box long dimension minus width / 2000; vias excluded','min':ordered[0],'median':ordered[len(ordered)//2],'max':ordered[-1],'geometry_sha256':sha(GEO),'spef_sha256':sha(SPEF)},indent=2))
 libs=list(dict.fromkeys(cfg['C']['libs']+cfg['U']['libs']))
 for label in samples:
  for freq in (200,300):
   out=ROOT/f'{label}-{freq}';out.mkdir(exist_ok=True)
   t='\n'.join('read_liberty {'+x+'}' for x in libs)+'\n'
   for role in ('C','U'):t+='read_verilog {'+str(ROOT/(role+'-v2')/'exported.v')+'}\n'
   t+='read_verilog {'+str(ROOT/'harness.v')+'}\nlink_design -hier cu_replay\n'
   t+=f'create_clock -name core -period {1000/freq:.10f} [get_ports clk]\n'
   t+='''set_clock_uncertainty 0.1 [all_clocks]
set_input_delay -max 0.8 -clock core [all_inputs -no_clocks]
set_input_delay -min 0.2 -clock core [all_inputs -no_clocks]
set_input_transition 0.05 [all_inputs -no_clocks]
set_output_delay -max 0.8 -clock core [all_outputs]
set_output_delay -min 0.2 -clock core [all_outputs]
set_load 2 [all_outputs]
set_propagated_clock [all_clocks]
'''
   t+='read_spef {'+str(ROOT/(label+'.spef'))+'}\n'
   for role in ('C','U'):t+='read_spef -path '+role+' {'+cfg[role]['spef']+'}\n'
   t+='''report_worst_slack -max -digits 9 > setup.rpt
report_worst_slack -min -digits 9 > hold.rpt
report_parasitic_annotation -report_unannotated > annotation.rpt
check_setup -verbose > constraints.rpt
foreach check {max_capacitance max_slew} {report_check_types -$check -format end -max_count 200 -digits 9 > $check.rpt}
set f [open crossing.tsv w]
puts $f "bit\tmode\tslack\tstartpoint\tendpoint"
'''
   rows=list(csv.DictReader((ROOT/'C-v2/ports.tsv').open(),delimiter='\t'))
   for bit in range(128):
    drivers=[r for r in rows if r['port']==f'outgoing_data[{bit}]' and r['pin_direction']=='OUTPUT'];assert len(drivers)==1
    r=drivers[0];pin='C/'+r['cell']+'/'+r['pin']
    t+=f'set driver [get_pins {{{pin}}}]\nif {{[llength $driver]!=1}} {{error "driver missing"}}\n'
    for mode in ('max','min'):
     t+=f'set paths [find_timing_paths -through $driver -path_delay {mode} -group_path_count 1 -sort_by_slack]\n'
     t+='if {[llength $paths]!=1} {error "crossing not timed"}\nset path [lindex $paths 0]\n'
     t+=f'puts $f "{bit}\t{mode}\t[get_property $path slack]\t[get_full_name [get_property $path startpoint]]\t[get_full_name [get_property $path endpoint]]"\n'
    if bit==0:t+='report_checks -through $driver -path_delay min_max -format full_clock_expanded -fields {slew capacitance input_pin net} -digits 9 > bit0.rpt\n'
   t+='close $f\nputs REPLAY_COMPLETE\n'
   (out/'run.tcl').write_text(t)
def run():
 jobs=sorted(ROOT.glob('*-[23]00/run.tcl'))
 def one(p):
  with (p.parent/'run.log').open('w') as f:
   rc=subprocess.call(['openroad','-no_init','-threads','2','-exit',str(p)],cwd=p.parent,stdout=f,stderr=subprocess.STDOUT)
  return {'case':p.parent.name,'exit':rc}
 with concurrent.futures.ThreadPoolExecutor(max_workers=7) as pool:result=list(pool.map(one,jobs))
 (ROOT/'run-status.json').write_text(json.dumps(result,indent=2))
 assert all(x['exit']==0 for x in result),result
if __name__=='__main__':
 import sys
 (prepare if sys.argv[1]=='prepare' else run)()
