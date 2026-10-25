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
 m=artifacts(stage);old=artifacts(previous);joint=m.get('candidate')=='incremental-joint-fourcap-50ps93';need(m.get('incremental_only')is True and m.get('candidate')in('incremental-hold-50ps-on-margin4','incremental-joint-fourcap-50ps93'),'sole frozen candidates');need((not joint and type(old.get('candidate'))is int and old['candidate']==4)or(joint and sha(previous/'manifest.json')=='c99f0fbfe94de9f6153791148ea00451caae682337938d0baeba715393c2cc87'),'exact source for each candidate');need(m['repair_hold_margin_ns']=='0.05'and type(m['repair_max_passes'])is int and m['repair_max_passes']==4096 and type(m['repair_max_iterations'])is int and m['repair_max_iterations']==4096 and type(m['repair_max_buffer_percent'])is int and m['repair_max_buffer_percent']==10,'fixed bounded recipe')
 if joint:
  init=(stage/'initialization.def').read_text();orig=(previous/'placed.def').read_text()
  for start,end in [('COMPONENTS ','END COMPONENTS'),('\nPINS ','END PINS'),('\nNETS ','END NETS')]:need(block(init,start,end)==block(orig,start,end),'DPL initialization leaves all exact cell geometry/pins/net connections unchanged')
  block((stage/'flow.log').read_text(),'BEGIN_NONMUTATING_DPL_INITIALIZATION','END_NONMUTATING_DPL_INITIALIZATION')
 t=(stage/'flow.tcl').read_text();commands=[x.strip()for x in t.splitlines()];gr=[x for x in commands if x.startswith('global_route ')];need(len(gr)==(4 if joint else 2)and all(x=='global_route -start_incremental -congestion_iterations 50'for x in gr[::2])and all(x.startswith('global_route -end_incremental -congestion_iterations 50 ')for x in gr[1::2])and '-guide_file 'in gr[-1],'only exact incremental intervals, no full reroute tail');need([x for x in commands if x.startswith('repair_')]==['repair_timing -hold -hold_margin 0.05 -max_passes 4096 -max_iterations 4096 -max_buffer_percent 10 -max_utilization 50 -verbose'],'only exact one hold operation');need(commands.count('detailed_placement -max_displacement {5 1}')==(2 if joint else 1) and 'set_debug_level GRT incr 2'in commands,'exact legalization/debug recipe')
 log=(stage/'flow.log').read_text();interval=block(log,'BEGIN_INCREMENTAL_CHANGE_INTERVAL','END_INCREMENTAL_CHANGE_INTERVAL');batches=[]
 for line in interval.splitlines():
  match=re.fullmatch(r'\[DEBUG GRT-incr\] (.*)',line)
  if not match:continue
  q=match[1]
  if q=='Dirty nets:':batches.append([])
  else:
   need(batches and q.startswith(' '),'ordered exact dirty batch');name=def_name(q.strip());need(name and name not in batches[-1],'unique dirty name in batch');batches[-1].append(name)
 need(batches and any(batches),'actual dirty batches include real updates; empty no-op batch retained');dirty=set(x for b in batches for x in b)
 before,bloc,bseg=read_graph(previous);after,aloc,aseg=read_graph(stage);created=set(after)-set(before);deleted=set(before)-set(after);same=set(before)&set(after);reconnected={n for n in same if before[n]!=after[n]};moved={n for n in set(bloc)&set(aloc)if bloc[n]!=aloc[n]};movednets={n for n,rs in after.items()if any(owner in moved for owner,pin in rs)};affected=created|reconnected|movednets
 finalmult={n for n,rs in after.items()if len(rs)>1};need(set(aseg)==finalmult,'all final multi-terminal nets globally routed, including changed nets');need(created<=dirty,'every new electrical net captured in dirty union');unlogged_reconnected=reconnected-dirty;need(all(n in bseg and n in aseg and bseg[n]==aseg[n]for n in unlogged_reconnected),'unlogged reconnected nets retain exact original main segments; pin access separately required')
 # Tool selects reroutes by grid pin positions, not terminal identity. Require actual
 # updated full RC sections for these explicit same-grid terminal substitutions.
 def spef_sections(folder):return {def_name(q[1]):q[3]for q in re.finditer(r'(?ms)^\*D_NET (\S+) (\S+)\n(.*?)^\*END\s*$',(folder/'route.spef').read_text())}
 oldrc=spef_sections(previous);newrc=spef_sections(stage);unlogged_proof=[]
 for n in sorted(unlogged_reconnected):
  need(n in oldrc and n in newrc and oldrc[n]!=newrc[n],'same-main-segment reconnected net has regenerated changed pin RC')
  unlogged_proof.append({'net':n,'before_pins':sorted(before[n]),'after_pins':sorted(after[n]),'before_rc_section_sha256':hashlib.sha256(oldrc[n].encode()).hexdigest(),'after_rc_section_sha256':hashlib.sha256(newrc[n].encode()).hexdigest(),'main_segments_byte_equivalent':True})
 changedseg={n for n in set(bseg)&set(aseg)if bseg[n]!=aseg[n]};unlogged_move=movednets-dirty;unchanged_main={n for n in unlogged_move if n in bseg and n in aseg and bseg[n]==aseg[n]};neighbors=changedseg-affected;unused={n for n in unlogged_move if n not in finalmult}
 need(unlogged_move<=unchanged_main|unused|changedseg,'every unlogged moved-pin net has explicit unchanged-grid/updated-segment/no-sink accounting')
 row={'status':'PASS_COMPLETE_INCREMENTAL_CHANGE_LEDGER_NOT_INDEPENDENT_RC_PHYSICS','source_manifest_sha256':sha(previous/'manifest.json'),'stage_manifest_sha256':sha(stage/'manifest.json'),'dirty_batches':batches,'empty_dirty_batch_indices':[i for i,b in enumerate(batches)if not b],'unlogged_reconnected_same_segments_regenerated_RC':unlogged_proof,'dirty_union':sorted(dirty),'created_nets':sorted(created),'deleted_nets':sorted(deleted),'reconnected_nets':sorted(reconnected),'moved_instances':[{'name':n,'before':bloc[n],'after':aloc[n]}for n in sorted(moved)],'moved_instance_nets':sorted(movednets),'affected_final_nets':sorted(affected),'changed_main_segment_nets':sorted(changedseg),'extra_changed_segment_nets_without_pin_changes':sorted(neighbors),'unlogged_moved_pin_same_main_segment_nets':sorted(unchanged_main),'unlogged_moved_pin_changed_main_segment_nets':sorted(unlogged_move&changedseg),'unlogged_moved_no_sink_nets':sorted(unused),'deleted_or_intermediate_dirty_names':sorted(dirty-set(after)),'final_multiterminal_RC_required':len(finalmult),'limitations':['Dirty log records actual selected update batches; callbacks can omit same-grid moves from rerouting and congestion may update extra neighbors.','Unchanged main segments do not imply unchanged pin-access RC. Every final pin is separately checked by full SPEF incidence/connectivity and same-tool replay; detailed route/RCX still required.','No claim of independent RC physics or genuine macro/PG/upstream-driver qualification.']}
 put(out/'incremental-change-ledger.json',row)
 return {'status':row['status'],'ledger_sha256':sha(out/'incremental-change-ledger.json'),'dirty_batches':len(batches),'dirty_unique_nets':len(dirty),'empty_batches':sum(not b for b in batches),'unlogged_reconnected_same_segments_updated_RC':len(unlogged_proof),'created_nets':len(created),'deleted_nets':len(deleted),'reconnected_nets':len(reconnected),'moved_cells':len(moved),'affected_final_nets':len(affected),'changed_main_segment_nets':len(changedseg),'extra_neighbor_segment_changes':len(neighbors),'unchanged_main_segment_moved_pin_nets':len(unchanged_main),'all_final_multiterminal_nets':len(finalmult)}
