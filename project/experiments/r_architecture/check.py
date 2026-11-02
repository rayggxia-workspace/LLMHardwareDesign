"""Verify recorded evidence bytes, input identity and measured-result accounting."""
from pathlib import Path
import hashlib,json,csv
R=Path(__file__).resolve().parents[3];D=R/'work/YUZE-LU/157'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    evidence=json.loads((D/'EVIDENCE.json').read_text())
    for row in evidence:assert sha(R/row['local'])==row['sha256'],row['local']
    baseline=json.loads((D/'BASELINE.json').read_text())
    for row in baseline['files']:
        if'frozen'in row:assert sha(R/row['frozen'].replace('\\','/'))==row['git_bytes_sha256']
    candidates=json.loads((D/'CANDIDATES.json').read_text())
    receipts=[]
    for kind in ('A0','A1','A2'):
        rec=json.loads((D/f'evidence/attempt001/results/{kind}-rtl/receipt.json').read_text());assert rec['passed'];assert sha(D/f'candidates/{kind}/block_v1_r.sv')==rec['rtl_sha256'];assert len(rec['initial_runs'])==3
        for run in rec['initial_runs'].values():assert run['passed']and run['checks']==379979 and run['cycles']==178456
        receipts.append(rec)
    manifests=[json.loads((D/f'evidence/{a}/results/corpus/MANIFEST.json').read_text())for a in('attempt003','attempt005')];assert manifests[0]==manifests[1];assert len(manifests[0]['cases'])==63
    results=list(csv.DictReader((D/'SYSTEMC_RESULTS.csv').open()));assert len(results)==3024
    for attempt in('attempt003','attempt005'):
        rr=[x for x in results if x['attempt']==attempt];assert len(rr)==1512;assert sum(x['status']=='PASS'for x in rr)==1212;assert sum(x['status']=='UNSUPPORTED_CURRENT_MODEL'for x in rr)==300
    rtl=json.loads((D/'evidence/attempt006/results/RTL_CORPUS_RESULTS.json').read_text());assert len(rtl)==63;assert sum(x['status']=='PASS'for x in rtl)==51;assert sum(x['status']=='UNSUPPORTED_ORIGINAL_CAPACITY'for x in rtl)==12
    for row in rtl:assert row['input_sha256']==next(x['sha256']for x in manifests[0]['cases']if x['path']==row['workload'])
    print('PASS: evidence hashes, frozen inputs, 9 RTL runs, 3024 model rows and 51/12 RTL corpus accounting. Not a complete architecture acceptance.')
if __name__=='__main__':main()
