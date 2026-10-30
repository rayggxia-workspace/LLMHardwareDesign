"""Capture explicitly ACTIVE phase evidence without pretending job closure."""
from pathlib import Path
import argparse,csv,datetime,gzip,hashlib,io,json,subprocess
REMOTE='/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027';HOST='yuzelu@10.129.166.172'
def capture(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    code=r'''
from pathlib import Path
import json,datetime,subprocess,hashlib
root=Path('/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027')
result={'scope':'ACTIVE_STATUS_OBSERVATION_NOT_CLOSED_JOB_OR_PHYSICAL_PASS','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'full_qualification':False,'jobs':{}}
for name,rel in [('LL_2832_variant','llsys_wire_pin_retention/r01'),('current_common_base','common_integration/deadline-current-r01/C')]:
 p=root/rel;q={'source_directory':str(p),'logs':{}}
 if (p/'execution.json').exists():
  raw=(p/'execution.json').read_bytes();q['native_receipt']=json.loads(raw);q['receipt_bytes_SHA256_at_observation']=hashlib.sha256(raw).hexdigest()
 for f in ['native.log','independent.log','place_PG.log','lower_route.log','placement_PG_stages.tsv','stages.tsv','RC_STA_stages.tsv']:
  path=p/f
  if path.exists():q['logs'][f]={'bytes':path.stat().st_size,'tail_lines':path.read_text(errors='replace').splitlines()[-15:]}
 result['jobs'][name]=q
result['own_selected_squeue']=subprocess.check_output(['squeue','-j','92855,93217,93243,93269,93317,93460,93472','-o','%.18i %.9T %.10M %R']).decode()
print(json.dumps(result))
'''
    raw=subprocess.check_output(['ssh',HOST,'python3 -'],input=code.encode());state=json.loads(raw);(out/'active_observation.json').write_bytes(raw)
    source=REMOTE+'/llsys_wire_pin_retention/r01/all_13507_actual_pin_correspondence.csv'
    expected=subprocess.check_output(['ssh',HOST,'sha256sum '+source]).decode().split()[0]
    zipped=subprocess.check_output(['ssh',HOST,'gzip -n -c -- '+source]);data=gzip.decompress(zipped)
    after=subprocess.check_output(['ssh',HOST,'sha256sum '+source]).decode().split()[0]
    assert expected==after==hashlib.sha256(data).hexdigest()
    rows=list(csv.DictReader(io.StringIO(data.decode())));assert len(rows)==13507 and len({r['pin'] for r in rows})==13507
    changed=[r['pin'] for r in rows if any(r['source_'+k]!=r['actual_'+k] for k in ['x0_um','y0_um','x1_um','y1_um'])];assert len(changed)==2832
    for r in rows:
        assert r['layer'] in ['metal5','metal6']
        for prefix in ['source','actual']:
            assert abs(float(r[prefix+'_x1_um'])-float(r[prefix+'_x0_um'])-.14)<1e-6 and abs(float(r[prefix+'_y1_um'])-float(r[prefix+'_y0_um'])-.14)<1e-6
    (out/'all_13507_actual_pin_correspondence.csv.gz').write_bytes(zipped)
    receipt={'scope':'COMPLETED_EDIT_SUBPHASE_COORDINATES_WITH_PARENT_JOB_VALIDATION_STILL_PENDING','source':source,'source_CSV_SHA256':expected,'lossless_gzip_SHA256':hashlib.sha256(zipped).hexdigest(),'actual_signal_rows':13507,'actual_changed_from_current10261_source_rows':2832,'original_M5_M6_and_0p14_size_verified':True,'native_full_DRC_connectivity_RC_STA_for_variant':'FOLLOW_NATIVE_RECEIPT_NOT_PROMOTED_BY_CSV_VALIDATION','active_observation_SHA256':hashlib.sha256(raw).hexdigest(),'full_qualification':False,'captured_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (out/'capture.json').write_text(json.dumps(receipt,indent=2)+'\n');print('ACTIVE_PHASE_CAPTURED',13507,'actual pins;2832 changed; validation pending; no job closure inferred')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();capture(a.out)
