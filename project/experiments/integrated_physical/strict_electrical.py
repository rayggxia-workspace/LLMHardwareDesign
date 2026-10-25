"""Full non-violator-filtered electrical reports; no fuzzy tolerance as margin."""
import argparse,re,sys
from decimal import Decimal
from common import *
from receive_physical import block
from strict_electrical_audit import parse_full
p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);sm=artifacts(a.stage);mods=load(a.stage/'final.json')['modules'];top=next(x for x in mods if x in('chain93','chain97'));net=mods[top]
lines=['set_thread_count 8',f'read_liberty {{{LIB}}}',f'read_db {{{a.stage}/final.odb}}',f'read_sdc {{{a.stage}/final.sdc}}']
if sm['stage']=='drt':lines += [f'read_spef -coupling_reduction_factor 1.0 {{{a.stage}/route.spef}}']
else:
 need(sm['stage']in('grt','routerepair','caprepair'),'routed actual RC source');lines += [f'source {{{P}/setRC.tcl}}',f'read_global_route_segments {{{a.stage}/route.segments}}','estimate_parasitics -global_routing']
for k in(1,10):
 for n,v in net['ports'].items():
  if v['direction']=='output':lines += [f'set_load {k} [get_ports {{{n}}}]']
 for check in('max_slew','max_capacitance','max_fanout'):
  lines += [f'puts "BEGIN_FULL_{check}_{k}"',f'report_check_types -{check} -max_count 1000000 -digits 9',f'puts "END_FULL_{check}_{k}"']
s=a.out/'probe.tcl';s.write_text(tcl_script(lines));command(a.out,'probe',[OR,'-exit',s],300);log=(a.out/'probe.log').read_text();scenarios=parse_full(a.stage,log)
put(a.out/'receipt.json',{'status':'PASS_RECEPTION_OF_ALL_REPORTED_ELECTRICAL_CHECKS_NOT_AUTOMATIC_CLOSURE','stage_directory':str(a.stage),'stage_manifest_sha256':sha(a.stage/'manifest.json'),'source':sources(),'all_electrical_maxima_met':all(c['strict_count']==0 for x in scenarios for c in x['checks'].values()),'scenarios':scenarios,'units':{'max_slew':'ns','max_capacitance':'fF','max_fanout':'count'},'limits':['Unfiltered report strict actual>limit comparison at nine reported decimals; never treats OpenSTA fuzzy zero tolerance as design margin.','No invented limit for external input driver/ideal source or unconstrained fanout; library full cap driver coverage independently checked by cap_distribution.','No physical or manufacturing signoff by this receipt alone.']});manifest(a.out,{'status':'COMPLETE_ELECTRICAL_REPORT_CHECKS_EXECUTED','source':sources(),'stage_directory':str(a.stage),'stage_manifest_sha256':sha(a.stage/'manifest.json'),'inputs':{n:sha(a.stage/n)for n in('final.odb','final.sdc','final.json')},'library_sha256':sha(LIB)});print('COMPLETE_ELECTRICAL_REPORT_CHECKS_EXECUTED')
