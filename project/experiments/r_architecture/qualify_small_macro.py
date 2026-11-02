"""Bind actual successful physical checks to the exact delivered macro files."""
from pathlib import Path
import argparse,hashlib,json,re
p=argparse.ArgumentParser()
for n in ['trial','candidate','analysis']:p.add_argument('--'+n,required=True)
a=p.parse_args();assert all(re.fullmatch(r'attempt[0-9]+',n)for n in[a.trial,a.analysis]);assert a.candidate=='B256'
base=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture')
trial=base/a.trial;analysis=base/a.analysis;physical=trial/'physical'
root=physical/'flow/results/nangate45'/('rarch157_'+a.candidate)/'base'
logs=physical/'flow/logs/nangate45'/('rarch157_'+a.candidate)/'base'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
read=lambda p:json.loads(p.read_text())
receipt=read(physical/'receipt.json');gate=read(trial/'evaluation'/ (a.candidate+'.json'))
io=read(trial/'results/IO_DELIVERY.json');geometry=read(analysis/'results'/a.candidate/'GEOMETRY.json')
export=read(analysis/'export/EXPORT.json');metrics=read(logs/'6_report.json');route=read(logs/'5_2_route.json')
lec=logs/'6_final_lec_check.log';text=lec.read_text()
checks={
 'producer':receipt['exit']==0 and receipt['candidate']==a.candidate and receipt['source_unchanged'] and receipt['pg_hook_observed'],
 'final_setup_hold':metrics['finish__timing__setup__ws']>=0 and metrics['finish__timing__hold__ws']>=0,
 'all_timing_electrical_counts_zero':all(metrics[k]==0 for k in ['finish__timing__drv__setup_violation_count','finish__timing__drv__hold_violation_count','finish__timing__drv__max_cap','finish__timing__drv__max_slew']),
 'router_drc_zero':route['detailedroute__route__drc_errors']==0,
 'final_lec': 'SAT solver finished: UNSAT'in text and 'Circuits are IDENTICAL'in text,
 'complete_original_gds_deck':gate.get('timing_pass')and gate.get('gds_exit')==gate.get('deck_exit')==0 and gate.get('full_gds_pass')and gate.get('full_gds_items')==0 and gate.get('deck_sha256')=='4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147'and gate.get('gds_sha256')==sha(root/'6_final.gds'),
 'actual_pin_and_supply_probe':io['passed']and io['signal_pin_shapes']==817 and io['signal_pin_geometry_identical']and io['actual_new_buffers']==168 and io['all_added_buffer_supplies_correct']and io['new']['trial']==a.trial and io['new']['odb_sha256']==sha(root/'6_final.odb'),
 'actual_route_geometry':geometry['centerline_matches_router_within_2um_each_layer']and geometry['def_sha256']==sha(root/'6_final.def')and geometry['spef_sha256']==sha(root/'6_final.spef')and all(s['exit']==0 for s in geometry['stages']),
 'abstract_views':export['passed']and export['source_final_unchanged']and export['trial']==a.trial and all(sha(Path(n))==r['sha256']for n,r in export['files'].items()),
 'unchanged_acceptance_sdc':sha(physical/'input.sdc')==sha(Path(__file__).parent/'physical.sdc'),
}
artifacts=list(root.glob('6_final.*'))+[root/'r_stream.lef',root/'r_stream_typ.lib']
evidence=[physical/'receipt.json',trial/'evaluation'/(a.candidate+'.json'),trial/'results/IO_DELIVERY.json',analysis/'results'/a.candidate/'GEOMETRY.json',analysis/'export/EXPORT.json',lec,logs/'6_report.json',logs/'5_2_route.json']
result=dict(passed=all(checks.values()),candidate=a.candidate,trial=a.trial,checks=checks,frequency_mhz=300,setup_ns=metrics['finish__timing__setup__ws'],hold_ns=metrics['finish__timing__hold__ws'],cell_area_um2=metrics['finish__design__instance__area'],die_um=[1000,1000],state_entries_per_bank=256,state_banks=2,state_bytes=2048,lanes=8,read_latency_cycles=0,scope='standalone small-R macro under frozen typical Nangate45/FreePDK45 checks; research stream ISA, not production-R replacement or full-model/system qualification',artifacts={str(f):dict(bytes=f.stat().st_size,sha256=sha(f))for f in artifacts},evidence={str(f):sha(f)for f in evidence})
Path('QUALIFICATION.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in ['artifacts','evidence']}));raise SystemExit(0 if result['passed']else 1)
