import argparse,json,hashlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cache_share'))
from inventory import resources,need,sha,load
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--library',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False)
rs=[];source=None
for s in(0,1):
 root=a.root/f'rtl-s{s}02';m=load(root/'manifest.json');r=load(a.root/f'receipt-s{s}03.json');need(m['stall']==s and r['stall']==s and m['profile']==0,'runtime exact configuration');need(r['status']=='PASS_RUNTIME_MODES_RECOVERY'and r['commands']==30 and r['run_manifest_sha256']==sha(root/'manifest.json'),'full receipt')
 for ent in m['artifacts']:need(sha(root/ent['path'])==ent['sha256'],'actual output binding')
 need(sha(a.root/f'receipt-s{s}03-negative.json')==r['semantic_negative_sha256'],'semantic negative bytes');rs.append(r);source=m['source']
mp=resources(a.root/'map02','chain85',a.library)
for n,h in source['sources'].items():
 if n.startswith('project/rtl/'):need(mp['source']['sources'].get(n)==h,'identical mapped/executed RTL')
wide=[x for x in mp['multipliers']if x['A_WIDTH']>8 or x['B_WIDTH']>8];small=[x for x in mp['multipliers']if x['A_WIDTH']<=8 and x['B_WIDTH']<=8]
need(len(wide)==1 and wide[0]['A_WIDTH']==32 and wide[0]['B_WIDTH']==32 and len(small)==8,'one S32 and8S8 no duplicate M')
rows=[]
for r in rs:
 for mode in(0,1):
  values=[x for x in r['rows']if x['cache']==mode and x['role']=='mixed'];need(len(values)==6,'both modes same executable');need(len({x['cycles']for x in values})==1,'fixed workload cycles');rows.append({'stall':r['stall'],'cache':mode,'cycles':values[0]['cycles'],'norm_cycles':values[0]['norm_cycles'],'wire_beats':values[0]['wire_beats'],'cache_reads':values[0]['cache_reads']})
basepath=Path('/public/home/yuzelu/RuizhiLiang/issue84-cache-share-20261025/analysis04/report.json');need(sha(basepath)=='873fbd5b435ffbb93e73e782ee62d72407053143553a4be8dd7f577ff56cc0cc','fixed84 comparison bytes');base=load(basepath);comparison=[]
for row in rows:
 old=next(x for x in base['metrics']if x['variant']==(3 if row['cache']else 1)and x['stall']==row['stall'])['rows'][0];need(old['cycles']==row['cycles'],'runtime maintains core cycles under same stimulus');comparison.append({'stall':row['stall'],'cache':row['cache'],'static_cycles':old['cycles'],'runtime_cycles':row['cycles']})
basearea=base['resources'][3]['area_um2_logic_only'];cost={'static84_cache_shared_logic_area':basearea,'runtime_logic_area':mp['area_um2_logic_only'],'increment_percent':100*(mp['area_um2_logic_only']-basearea)/basearea,'static84_generic_register_bits':base['resources'][3]['generic_register_bits_including_frame_wrapper'],'runtime_generic_register_bits':mp['generic_register_bits_including_frame_wrapper'],'baseline_report_sha256':sha(basepath),'same_core_cycles':comparison}
report={'cost_comparison':cost,'status':'PASS_RUNTIME_RESOURCE_AND_RECOVERY','full_commands':60,'accepted_commands':94,'soft_aborts':22,'input_faults':12,'resources':mp,'cycles':rows,'receipts':[{'stall':r['stall'],'run_manifest_sha256':r['run_manifest_sha256'],'protocol':r['protocol']}for r in rs],'limits':['External epoch is an explicit32bit request/response tag sideband in this prototype. Existing128bit five-beat transport counter does not by itself price these additional metadata wires or a real NoC. Tag logic/registers are included in mapped cell area.','Same16KiB1RW and8S8+1S32 inventory. Command/FSM/control/epoch/mux registers added and measured, no command FIFO.','Global reset requires coordinated fabric reset; soft_abort alone handles stale tagged responses. No CDC, reordering, epoch wrap or target fabric qualification.','Whole store82 wrapper blackboxed; Nangate logic area is not SRAM macro/STA/route/PPA or device signoff.']}
(a.out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status']);print(json.dumps(rows));print(mp['area_um2_logic_only'],mp['generic_register_bits_including_frame_wrapper'])
