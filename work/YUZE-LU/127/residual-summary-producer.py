import json,sys,subprocess
from pathlib import Path
sys.path.insert(0,'project/experiments/block_v1/macro_boundary_qa')
from audit import file_sha
root=Path.cwd()
result={'schema':'block-v1-input-output-residual-summary/1','qualified_hard_macro':False,'flat_abstract_boundary_qualified':False,
 'producer_sha256':file_sha(Path(__file__)),'code_commit_parent':'79d0dc1db3209fad53c675d2bb1511ebd89b5dfb',
 'analysis_code_sha256':file_sha(Path('project/experiments/block_v1/macro_boundary_qa/input_driver_residual.py')),
 'candidate_input_decomposition':{},'output_wire_controls':[]}
for pol in ('a','c'):
 p=Path(f'.local/qa127/input-driver-residual-{pol}-001.json')
 result['candidate_input_decomposition'][pol]={'path':str(p),'sha256':file_sha(p),'result':json.loads(p.read_text())}
for resistance in (1,20000):
 folder=Path(f'.local/qa127/native-output-wire-{resistance}-001')
 proof=json.loads((folder/'native-control-report.json').read_text())
 detail={'resistance_ohm':resistance,'path':str(folder),'report_sha256':file_sha(folder/'native-control-report.json'),
  'proof':proof,'cases':[],'exact_reread_receipts':{}}
 for rname in ('low-r','high-r'):
  for driver in ('BUF_X2','BUF_X1'):
   pair=folder/f'{rname}-{driver}'
   full,macro=[json.loads((pair/v/'observed.json').read_text())for v in ('flat','abstract')]
   full_outputs={tuple(r['key']):r for r in full['observations']if r['key'][0]=='output'}
   deltas=[{'key':r['key'],'slack_delta_ps':1000*(r['slack_ns']-full_outputs[tuple(r['key'])]['slack_ns'])}
    for r in macro['observations']if r['key'][0]=='output']
   values=[abs(x-y)*1000 for x,y in zip(full['ports']['q']['slew_ns'],macro['ports']['q']['slew_ns'])]
   detail['cases'].append({'input':rname,'driver':driver,'max_output_slack_delta_ps':max(abs(r['slack_delta_ps'])for r in deltas),
    'output_slack_deltas':deltas,'max_output_slew_delta_ps':max(values),
    'full_output_slew_ns':full['ports']['q']['slew_ns'],'macro_output_slew_ns':macro['ports']['q']['slew_ns'],
    'receipt_sha256':file_sha(pair/'receipt.json'),'receipt':json.loads((pair/'receipt.json').read_text()),
    'flat_observed_sha256':file_sha(pair/'flat/observed.json'),'abstract_observed_sha256':file_sha(pair/'abstract/observed.json')})
  exact=folder/f'{rname}-exact-reread'
  detail['exact_reread_receipts'][rname]={'sha256':file_sha(exact/'receipt.json'),'receipt':json.loads((exact/'receipt.json').read_text())}
 result['output_wire_controls'].append(detail)
 print(resistance,json.dumps([{k:c[k]for k in ['input','driver','max_output_slack_delta_ps','max_output_slew_delta_ps','full_output_slew_ns','macro_output_slew_ns']}for c in detail['cases']],indent=2))
path=Path('work/YUZE-LU/127/input-output-residual-summary.json')
path.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
with Path('work/YUZE-LU/127/synthetic-test-results.txt').open('w',encoding='utf-8')as f:
 completed=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','project/experiments/block_v1/macro_boundary_qa','-p','test_*.py','-v'],stdout=f,stderr=subprocess.STDOUT)
assert completed.returncode==0
