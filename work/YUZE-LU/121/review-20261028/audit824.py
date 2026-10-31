from pathlib import Path
import hashlib,json,shutil
b=Path('work/YUZE-LU/121/review-20261028');delivery=Path('work/YUZE-LU/121/delivery-300mhz/V');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
folders=['v-805-drc-final-813','v-805-delivery-geometry-818','v-806-interface-821','v-806-load-rc-823']
for name in folders:
 d=json.loads((b/name/'index.json').read_bytes())
 for n,r in d['files'].items():
  p=b/name/n;assert p.stat().st_size==r['bytes']and sha(p)==r['sha256']
n=b/'v-805-delivery-geometry-818/block-v1-20261031-805/tasks'
source=sha(n/'revision300-final-source-v/receipt.json');assert source=='9ef42c0fb71fdf9f076f37f4c746631eb1c9e96d0d7b9fae65d7b4d90e425009'
reports={}
for mode in ('physical','drc','final-function','formal'):
 p=n/('revision300-'+mode+'-v');r=json.loads((p/'receipt.json').read_bytes());x=json.loads((p/('five-macro-'+mode+'.json')).read_bytes());assert r['passed']and x['passed']and x['source_receipt_sha256']==source;reports[mode]=x
assert all(reports['physical']['checks'].values())and reports['physical']['timing']['passed']
assert reports['physical']['timing']['timed_endpoints']['endpoint_count']==27066
assert not reports['drc']['native_report'].strip()and reports['drc']['full_deck']['total_items']==0
assert reports['drc']['deck_sha256']=='4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147'
f=reports['final-function'];assert set(f['initial_runs'])=={'all-ones','random-121','random-122'}
for r in f['initial_runs'].values():assert r['result']['passed']and r['result']['checks']==574942 and r['result']['cycles']==425971
lec=reports['formal']['strict_native_lec'];assert lec['passed']and all(lec['checks'].values());assert reports['formal']['source_final_function_receipt_sha256']==sha(n/'revision300-final-function-v/receipt.json')
g=json.loads((delivery/'native-geometry.json').read_bytes());assert g['passed']and g['original_odb_unchanged']and g['native_def_rect_complete']and g['native_geometry_counts']['wire-rect']==400
ix=json.loads((b/'v-805-delivery-geometry-818/index.json').read_bytes());assert ix['six_final_files_actual_remote_hash_verified']and ix['image_actually_viewed']
image=json.loads((delivery/'image-source.json').read_bytes());assert image['actually_viewed']and sha(delivery/'block_v1_v.png')==image['sha256']
p=b/'v-806-interface-821/block-v1-20261031-806/tasks/revision300-escape-v';escape=json.loads((p/'revision300-escape.json').read_bytes());assert escape['passed']and escape['all_signal_bits']==escape['simultaneous_connected_bits']==277
plots=json.loads((delivery/'interface/plot-manifest.json').read_bytes());assert len(plots['pngs_actually_viewed'])==3
loadbase=b/'v-806-load-rc-823/block-v1-20261031-806/tasks';summary={}
control=b/'boundary-rc-0448/tasks/revision300-boundary-rc-control/receipt.json';assert control.is_file()
for mode in ('load-v-approved','load-v-base','load-v-high','boundary-rc-v-base','boundary-rc-v-high'):
 p=loadbase/('revision300-'+mode);kind='boundary-rc'if mode.startswith('boundary')else'load';r=json.loads((p/('revision300-'+kind+'.json')).read_bytes());t=r['timing']['timed_endpoints'];assert r['passed']and r['experiment_completed']
 assert r['source_escape_receipt_sha256']==sha(b/'v-806-interface-821/block-v1-20261031-806/tasks/revision300-escape-v/receipt.json')
 if kind=='boundary-rc':
  assert r['control_receipt_sha256']==sha(control)
  pi=r['all_input_output_clock_pi_rc'];assert pi['passed']and pi['port_count']==277 and pi['native_parasitics_preserved']
  native=json.loads((delivery/'final-native.json').read_bytes());assert pi['native_spef_sha256']==native['final_files']['6_final.spef']['sha256']
 else:assert r['actual_wrong_load_negative_rejected']and r['output_count']==133
 if mode=='boundary-rc-v-high':assert not r['timing']['passed']and t['electrical']['capacitance']['count']==3
 else:assert r['timing']['passed']and t['electrical']['capacitance']['count']==0
 assert t['endpoint_count']==27066 and t['minimum_setup_ns']==.012849 and t['minimum_hold_ns']==.029884 and t['electrical']['slew']['count']==0
 summary[mode]=dict(actual_sta_passed=r['timing']['passed'],minimum_setup_ns=t['minimum_setup_ns'],minimum_hold_ns=t['minimum_hold_ns'],capacitance_violations=t['electrical']['capacitance']['count'],slew_violations=t['electrical']['slew']['count'],receipt_sha256=sha(p/'receipt.json'),report_sha256=sha(p/('revision300-'+kind+'.json')))
shutil.copyfile('.local/issue121/collect823.py',b/'v-806-load-rc-823/collect823.py')
report=dict(passed=True,macro='V',native_macro_delivery_verified=True,base_interface_pi_scenario_passed=True,high_interface_pi_scenario_passed=False,complete_m11_m12_system_qualified=False,five_macro_goal_complete=False,source_receipt_sha256=source,native_run=804,final_run=805,interface_run=806,implementation_count=1,native_routing_layers=['metal'+str(i)for i in range(1,11)],signal_bits=277,actual_timed_endpoints=27066,full_gds_categories=129,full_gds_items=0,all_three_final_netlist_initializations_passed=True,strict_all_input_output_lec_passed=True,complete_native_geometry_and_original_odb_preserved=True,all_six_final_files_actual_remote_sha_verified=True,actual_gds_and_three_interface_plots_viewed=True,sensitivity_results=summary,high_pi_failure='cmd_index[4], cmd_valid, cmd_index[7] exceed121.154999fF input cap limit; worst134.650940fF. Setup/hold remain positive; no waiver/source/constraint change.',evidence_indexes={name:sha(b/name/'index.json')for name in folders},scope='One base V macro at approved300MHz Nangate45 conditions plus full277-port finite interface geometry and explicitly limited base pi RC. High1.5x R/C sensitivity fails3 input cap checks and stays failed. No process-qualified12-layer system, hierarchicalLib, whole-model throughput/quality or margin implementation claim. R404 and its final gates remain.')
(b/'verification-824.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');(delivery/'acceptance.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('V native/base finite interface acceptance audit PASS; high3-cap failure retained; R incomplete')
