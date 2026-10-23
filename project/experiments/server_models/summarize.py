"""Aggregate executed stage evidence without treating numeric errors as acceptance."""
import argparse,json
from pathlib import Path

def load(p):return json.loads(Path(p).read_text())
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if a.out.exists():raise ValueError('refuse overwrite')
 result={'schema':'server-batch-readout/1','model_quality_accepted':False,'target_hardware_validated':False,'models':{}}
 for model,folder in [('gemma','gemma-capture01'),('qwen25','qwen25-gqa01'),('qwen35','qwen35-gqa01'),('phi','phi-reserved01')]:
  cap=load(a.root/folder/'manifest.json');strict=load(a.root/(model+'-strict02')/'index.json');source_audit=load(a.root/(model+'-export-source02.json'))
  if cap['status']!='PASS'or strict['status']!='PASS'or source_audit['status']!='PASS':raise ValueError('required capture/format/source stage failed '+model)
  row={'model':cap['model'],'capture_source_commit':cap['source_commit'],'capture_script_seconds':cap['seconds'],'capture_peak_RSS_bytes':cap['actual_peak_RSS_bytes'],'versions':cap['versions'],'threads':cap['threads'],'case_names':[c['name']for c in cap['cases']],'group_Q_heads':cap['GQA_group'],'head_dim':cap['head_dim'],'selected_layers':cap['selected_layers'],'sealed_reserved':cap['sealed_reserved'],'raw_capture':cap['artifacts']['selected-raw.npz'],'strict_validated_tensors':sum(r['validated_tensors']for r in strict['cases']),'KV':[]}
  row['export_source_audit']=source_audit
  for c in cap['cases']:
   kv={'case':c['name'],'full_logical_bytes':c['full_KV']['logical_bytes'],'full_backing_storage_bytes':c['full_KV']['deduplicated_storage_bytes']}
   for mode,check in c['checks'].items():
    kv[mode+'_last33_logits']=check['last33_logits'];kv[mode+'_GQA_max_relative_l2']=max(e['relative_l2']for e in check['GQA'].values())
    kv[mode+'_initial_logical_bytes']=check['KV_events'][0]['KV']['logical_bytes'];kv[mode+'_initial_backing_storage_bytes']=check['KV_events'][0]['KV']['deduplicated_storage_bytes'];kv[mode+'_final_logical_bytes']=check['KV_events'][-1]['KV']['logical_bytes'];kv[mode+'_final_backing_storage_bytes']=check['KV_events'][-1]['KV']['deduplicated_storage_bytes']
   row['KV'].append(kv)
  if model!='phi':
   qm=load(a.root/(model+'-integer01')/'manifest.json');qr=load(a.root/(model+'-independent01.json'));linear=load(a.root/(model+'-integer01')/'linear.json');attention=load(a.root/(model+'-integer01')/'attention.json')
   if qm['status']!='PASS'or qr['status']!='PASS':raise ValueError('required integer/readback stage failed '+model)
   row.update(integer_source_commit=qm['source_commit'],integer_seconds=qm['seconds'],independent_checks=qr['checks'],linear_profiles=[],attention_formats=[])
   for label,profile in sorted({(r['linear'],r['profile'])for r in linear}):
    rr=[r for r in linear if r['linear']==label and r['profile']==profile]
    row['linear_profiles'].append({'linear':label,'profile':profile,'cases':len(rr),'worst_before_RQ_rmse':max(r['before_RQ_error']['relative_rmse']for r in rr),'worst_after_RQ_rmse':max(r['after_RQ_error']['relative_rmse']for r in rr),'all_exploratory_local_screen_passed':all(r['exploratory_local_screen_passed']for r in rr),'output_saturation_count':sum(r['output_saturation_count']for r in rr),'A_clipping':sum(r['A_clipping']for r in rr),'max_coarse_signed_bound_bits':max(r['required_signed_bits_for_this_scale_matrix']for r in rr),'scope':'selected16 outputs/fullK, local5% screen only, not full-model quality'})
   for layer,kbits,pbits in sorted({(r['layer'],r['KV_bits'],r['P_bits'])for r in attention}):
    rr=[r for r in attention if r['layer']==layer and r['KV_bits']==kbits and r['P_bits']==pbits]
    row['attention_formats'].append({'layer':layer,'KV_bits':kbits,'P_bits':pbits,'worst_attention_rmse':max(r['attention_error']['relative_rmse']for r in rr),'max_P_zero_fraction':max(r['P_zero_fraction']for r in rr),'K_clips':sum(r['K_clips']for r in rr),'V_clips':sum(r['V_clips']for r in rr),'max_PV_signed_bound_bits':max(r['cost']['PV_accumulator_required_signed_bound_bits']for r in rr),'signed8_limb_products_per_base_PV_MAC':rr[0]['cost']['P16_or_KV16_limb_products_per_base_MAC'],'scope':'selected completeGQA group, static KV calibration, FP64 softmax fallback'})
  result['models'][model]=row
 result['status']='PASS_EXECUTED_STAGES';a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps({'status':result['status'],'models':list(result['models'])}))
if __name__=='__main__':main()
