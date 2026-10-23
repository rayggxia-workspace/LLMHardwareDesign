"""Repack selected linear traffic at causal call boundaries; no cycle/PPA claim."""
import argparse,hashlib,json,math
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def packet(raw):
 if raw<0:raise ValueError('negative payload')
 return 0 if raw==0 else math.ceil((raw+math.ceil(raw/1984)*64)/64)*64

def account(row):
 c=row['cost'];n=row['outputs'];rows=row['rows'];groups=row['groups']
 if c['A_scale_bytes']%rows:raise ValueError('row scale layout')
 ae=c['A_scale_bytes']//rows
 sizes=[1]*rows if row['case'].endswith('.decode') else[rows]
 final=sum(packet(r*n+n+32)for r in sizes)
 compact=sum(packet(r*groups*n*4+r*ae+32)for r in sizes)
 explicit=sum(packet(r*groups*n*4+r*groups*n*2+r*n*2+32)for r in sizes)
 return {'linear':row['linear'],'profile':row['profile'],'case':row['case'],'selected_rows':rows,'groups':groups,'causal_calls':len(sizes),'final_I8_wire_bytes':final,'shared_I32_compact_partial_wire_bytes':compact,'shared_I32_explicit_unit_wire_bytes':explicit,'shared_additional_partial_wire_128bit_beats':compact//16,'static_W_Y_bias_resident_bytes':c['W_scale_bytes']+c['Y_scale_bytes']+c['bias_S32Q20_bytes'],'initial_static_metadata_packet_bytes':packet(c['W_scale_bytes']+c['Y_scale_bytes']+c['bias_S32Q20_bytes']),'encoded_A_bytes':c['A_i8_bytes'],'encoded_W_bytes':c['W_i8_bytes'],'A_scale_bytes':c['A_scale_bytes'],'W_scale_bytes':c['W_scale_bytes'],'partial_materialization_RW_bytes':2*c['INT32_partial_bytes'],'per_row_all_group_I32_partial_scratch_bytes':groups*n*4,'per_row_streaming_I32_acc_bytes':n*4,'per_row_streaming_I64_acc_bytes':n*8,'per_row_complete_source_S32_bytes':row['K']*4,'source_scratch_budget_bytes':16384,'source_passes_if_complete_row_does_not_fit':c['row_source_passes_for_16KiB'],'range_certificate_U32_L1_bytes':groups*n*4,'range_guard_terms_per_selected_row':groups*n,'scope':'selected16 outputs/fullK; decode packets separate at every token, prefill selected rows batched once only; compact route assumes static W/Y/bias resident, explicit route carries product units; no FIFO/scheduler, no measured port cycles; partial materialization and streaming are alternatives, not simultaneous costs'}

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--binding',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if a.out.exists():raise ValueError('refuse overwrite')
 binding=json.loads(a.binding.read_text())
 if sha(Path(__file__))!=binding['cost_readout_sha256']:raise ValueError('source SHA')
 result={'status':'PASS','source_commit':binding['commit'],'models':{},'hardware_performance_accepted':False,'scope':__doc__}
 for model in ['gemma','qwen25','qwen35']:
  q=a.root/(model+'-integer01');m=json.loads((q/'manifest.json').read_text());f=q/'linear.json'
  if sha(f)!=m['artifacts']['linear.json']['sha256']:raise ValueError('linear source SHA')
  result['models'][model]={'integer_manifest_sha256':sha(q/'manifest.json'),'rows':[account(r)for r in json.loads(f.read_text())]}
 a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps({'status':'PASS','linear_cases':sum(len(m['rows'])for m in result['models'].values())}))
if __name__=='__main__':main()
