"""Independent enumeration of changed nets and all captured incremental batches."""
import re,collections
from common import *
from receive_physical import block,def_name

def read_graph(folder):
 text=(folder/'placed.def').read_text();netsec=block(text,'\nNETS ','END NETS').split(';',1)[1];refs={}
 for n,body in re.findall(r'(?s)-\s+(\S+)\s+(.*?);',netsec):
  pins=frozenset((def_name(owner),def_name(pin))for owner,pin in re.findall(r'\(\s*(\S+)\s+(\S+)\s*\)',body.split('+',1)[0]));name=def_name(n)
  if pins:need(name not in refs,'unique physical electrical net');refs[name]=pins
 comp=block(text,'COMPONENTS ','END COMPONENTS').split(';',1)[1];loc={}
 for n,typ,body in re.findall(r'(?s)-\s+(\S+)\s+(\S+)\s+(.*?);',comp):
  m=re.search(r'\+ (?:PLACED|FIXED) \(\s*(\d+) (\d+) \) (\S+)',body);need(m is not None,'placed actual cell');loc[def_name(n)]=(typ,*m.groups())
 seg={}
 for m in re.finditer(r'(?ms)^(\S+)\n\(\n(.*?)^\)\s*$',(folder/'route.segments').read_text()):
  n=def_name(m[1]);need(n not in seg and n in refs,'unique routed electrical net');seg[n]=sorted(x.strip()for x in m[2].strip().splitlines())
 return refs,loc,seg

def audit_incremental(stage,previous,out):
 m=artifacts(stage);old=artifacts(previous);need(m.get('incremental_only')is True and m.get('candidate')=='incremental-hold-50ps-on-margin4','sole frozen candidate');need(type(old.get('candidate'))is int and old['candidate']==4,'margin source');need(m['repair_hold_margin_ns']=='0.05'and type(m['repair_max_passes'])is int and m['repair_max_passes']==4096 and type(m['repair_max_iterations'])is int and m['repair_max_iterations']==4096 and type(m['repair_max_buffer_percent'])is int and m['repair_max_buffer_percent']==10,'fixed bounded recipe')
 t=(stage/'flow.tcl').read_text();commands=[x.strip()for x in t.splitlines()];gr=[x for x in commands if x.startswith('global_route ')];need(len(gr)==2 and gr[0]=='global_route -start_incremental -congestion_iterations 50'and gr[1].startswith('global_route -end_incremental -congestion_iterations 50 -guide_file '),'only one incremental interval, no full reroute tail');need([x for x in commands if x.startswith('repair_')]==['repair_timing -hold -hold_margin 0.05 -max_passes 4096 -max_iterations 4096 -max_buffer_percent 10 -max_utilization 50 -verbose'],'only exact one hold operation');need(commands.count('detailed_placement -max_displacement {5 1}')==1 and 'set_debug_level GRT incr 2'in commands,'exact legalization/debug recipe')
 log=(stage/'flow.log').read_text();interval=block(log,'BEGIN_INCREMENTAL_CHANGE_INTERVAL','END_INCREMENTAL_CHANGE_INTERVAL');batches=[]
 for line in interval.splitlines():
  match=re.fullmatch(r'\[DEBUG GRT-incr\] (.*)',line)
  if not match:continue
  q=match[1]
  if q=='Dirty nets:':batches.append([])
  else:
   need(batches and q.startswith(' '),'ordered exact dirty batch');name=def_name(q.strip());need(name and name not in batches[-1],'unique dirty name in batch');batches[-1].append(name)
 need(batches and all(batches),'complete nonempty dirty batch log');dirty=set(x for b in batches for x in b)
 before,bloc,bseg=read_graph(previous);after,aloc,aseg=read_graph(stage);created=set(after)-set(before);deleted=set(before)-set(after);same=set(before)&set(after);reconnected={n for n in same if before[n]!=after[n]};moved={n for n in set(bloc)&set(aloc)if bloc[n]!=aloc[n]};movednets={n for n,rs in after.items()if any(owner in moved for owner,pin in rs)};affected=created|reconnected|movednets
 finalmult={n for n,rs in after.items()if len(rs)>1};need(set(aseg)==finalmult,'all final multi-terminal nets globally routed, including changed nets');need((created|reconnected)-dirty==set(),'every created/reconnected electrical net captured in dirty union')
 changedseg={n for n in set(bseg)&set(aseg)if bseg[n]!=aseg[n]};unlogged_move=movednets-dirty;unchanged_main={n for n in unlogged_move if n in bseg and n in aseg and bseg[n]==aseg[n]};neighbors=changedseg-affected;unused={n for n in unlogged_move if n not in finalmult}
 need(unlogged_move<=unchanged_main|unused|changedseg,'every unlogged moved-pin net has explicit unchanged-grid/updated-segment/no-sink accounting')
 row={'status':'PASS_COMPLETE_INCREMENTAL_CHANGE_LEDGER_NOT_INDEPENDENT_RC_PHYSICS','source_manifest_sha256':sha(previous/'manifest.json'),'stage_manifest_sha256':sha(stage/'manifest.json'),'dirty_batches':batches,'dirty_union':sorted(dirty),'created_nets':sorted(created),'deleted_nets':sorted(deleted),'reconnected_nets':sorted(reconnected),'moved_instances':[{'name':n,'before':bloc[n],'after':aloc[n]}for n in sorted(moved)],'moved_instance_nets':sorted(movednets),'affected_final_nets':sorted(affected),'changed_main_segment_nets':sorted(changedseg),'extra_changed_segment_nets_without_pin_changes':sorted(neighbors),'unlogged_moved_pin_same_main_segment_nets':sorted(unchanged_main),'unlogged_moved_pin_changed_main_segment_nets':sorted(unlogged_move&changedseg),'unlogged_moved_no_sink_nets':sorted(unused),'deleted_or_intermediate_dirty_names':sorted(dirty-set(after)),'final_multiterminal_RC_required':len(finalmult),'limitations':['Dirty log records actual selected update batches; callbacks can omit same-grid moves from rerouting and congestion may update extra neighbors.','Unchanged main segments do not imply unchanged pin-access RC. Every final pin is separately checked by full SPEF incidence/connectivity and same-tool replay; detailed route/RCX still required.','No claim of independent RC physics or genuine macro/PG/upstream-driver qualification.']}
 put(out/'incremental-change-ledger.json',row)
 return {'status':row['status'],'ledger_sha256':sha(out/'incremental-change-ledger.json'),'dirty_batches':len(batches),'dirty_unique_nets':len(dirty),'created_nets':len(created),'deleted_nets':len(deleted),'reconnected_nets':len(reconnected),'moved_cells':len(moved),'affected_final_nets':len(affected),'changed_main_segment_nets':len(changedseg),'extra_neighbor_segment_changes':len(neighbors),'unchanged_main_segment_moved_pin_nets':len(unchanged_main),'all_final_multiterminal_nets':len(finalmult)}
