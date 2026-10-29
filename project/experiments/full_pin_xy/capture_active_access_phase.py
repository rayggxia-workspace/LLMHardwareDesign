"""Capture a finished actual edit phase without claiming overall job closure."""
from pathlib import Path
from collections import Counter
import base64,csv,datetime,gzip,hashlib,io,json,subprocess
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/experiments/issue-126-full-pin/data/deadline_phase_snapshots'
CODE=r'''
from pathlib import Path
import base64,datetime,gzip,hashlib,json
root=Path('/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027');p=root/'all_llsys_access_stubs/r03'
q=json.loads((p/'execution.json').read_text());assert q['native_returncodes']['actual_stub_edit']==0
stages=(p/'actual_stub_edit.stages.tsv').read_text();assert all(name+'\tEXECUTED' in stages for name in ['actual_all_selected_stubs_and_original_layer_pins','VDD','VSS'])
csv=p/'all_13507_actual_pin_correspondence.csv';raw=csv.read_bytes();digest=hashlib.sha256(raw).hexdigest()
def sha(file):
 h=hashlib.sha256()
 with file.open('rb') as f:
  for chunk in iter(lambda:f.read(4*1024*1024),b''):h.update(chunk)
 return h.hexdigest()
odb=p/'routed.odb';before=sha(odb)
result={'scope':'FINISHED_ACTUAL_EDIT_PHASE_SNAPSHOT_NOT_TERMINAL_JOB_OR_PHYSICAL_QUALIFICATION','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':str(p),'driver_commit':q['driver_commit'],'job':q['scheduler_job'],'overall_job_closed_at_capture':bool(q.get('completed_utc')),'full_qualification':False,'native_returncodes_snapshot':q['native_returncodes'],'actual_edit_PG_stages':stages,'source_ODB':str(odb),'source_ODB_SHA256':before,'source_original_C_inputs':q['source_SHA'],'all_pin_CSV_SHA256':digest,'native_single_terminal_no_peer_or_wire':q['native_proven_single_terminal_without_internal_peer_or_wire'],'requested_actual_XY':q['actual_requested_XY_and_stub_count'],'native_fresh_AP_RC_STA':'Separate stages; no success inferred from this snapshot','csv_gzip_base64':base64.b64encode(gzip.compress(raw)).decode()}
assert csv.read_bytes()==raw and sha(odb)==before
print(json.dumps(result))
'''
def run():
    result=json.loads(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -'],input=CODE.encode()));payload=gzip.decompress(base64.b64decode(result.pop('csv_gzip_base64')))
    assert hashlib.sha256(payload).hexdigest()==result['all_pin_CSV_SHA256'];rows=list(csv.DictReader(io.StringIO(payload.decode())))
    assert len(rows)==len({r['pin'] for r in rows})==13507
    changed=sum(r['changed_from_complete_PG_C']=='True' for r in rows);assert changed==result['requested_actual_XY']==9517
    assert all(r['layer'] in ['metal5','metal6'] and abs(float(r['actual_x1_um'])-float(r['actual_x0_um'])-.14)<1e-7 and abs(float(r['actual_y1_um'])-float(r['actual_y0_um'])-.14)<1e-7 for r in rows)
    result['actual_complete_CSV_validation']={'all_original_pins':13507,'changed_XY':changed,'M5_M6_original_0p14_size_preserved':True,'layer_counts':dict(Counter(r['layer'] for r in rows)),'original_raw_native_pin_contract_preceded_this_export':True}
    OUT.mkdir(exist_ok=True);stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ');name='actual_access_stubs_r03_'+stamp
    (OUT/(name+'.csv.gz')).write_bytes(gzip.compress(payload,mtime=0));result['coordinate_artifact']='data/deadline_phase_snapshots/'+name+'.csv.gz'
    (OUT/(name+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('ACTUAL_PHASE_CAPTURED',name,'13507 pins /9517 actual XY; overall physical qualification NOT claimed')
if __name__=='__main__':run()
