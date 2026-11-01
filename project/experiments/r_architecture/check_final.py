"""Check measured accounting and complete proof certificates; no signoff inference."""
from pathlib import Path
import hashlib,json,csv,gzip,ast,tarfile
R=Path(__file__).resolve().parents[3];D=R/'work/YUZE-LU/157';E=D/'evidence/extended'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def check_proof(n,kind):
 p=E/f'attempt{n:03d}/results/{kind}-full-proof';archive=tarfile.open(p/'PARTITION_CERTIFICATES.tar.gz')if(p/'PARTITION_CERTIFICATES.tar.gz').exists()else None;rec=load(p/'receipt.json');assert rec['passed']and rec['exact_cover']and rec['all_state_and_all_external_outputs']and rec['no_blackboxes']and rec['no_assumed_internal_invariants']
 cov=p/'COVERAGE.json.gz';data=gzip.decompress(cov.read_bytes())if cov.exists()else(p/'COVERAGE.json').read_bytes();assert hashlib.sha256(data).hexdigest()==rec['coverage_sha256'];c=json.loads(data);bits=[tuple(x)for group in c['groups']for x in group['bits']];assert len(bits)==len(set(bits))==rec['state_bits']+rec['original_output_bits']==146269
 parts=load(p/'PARTS.json');assert len(parts)==rec['partitions']==rec['proved_partitions']==772;assert all(x['passed']for x in parts)
 for part in parts:
  f=p/('part%04d'%part['id'])/'complete.log.gz';b=gzip.decompress(f.read_bytes())if f.exists()else f.with_suffix('').read_bytes()if f.with_suffix('').exists()else archive.extractfile('part%04d/complete.log'%part['id']).read()
  assert hashlib.sha256(b).hexdigest()==part['log_sha256'];assert b'SUCCESS!'in b
 assert sha(D/'candidates'/kind/'block_v1_r.sv')==rec['rtl_sha256'];return rec
def main():
 for row in load(D/'EVIDENCE.json'):assert sha(R/row['local'])==row['sha256'],row['local']
 for row in load(D/'BASELINE.json')['files']:
  if'frozen'in row:assert sha(R/row['frozen'].replace('\\','/'))==row['git_bytes_sha256']
 check_proof(35,'A1');check_proof(51,'A2h')
 for n,k in [(35,'A1'),(51,'A2h')]:
  rec=load(E/f'attempt{n:03d}/results/{k}-map/receipt.json');assert rec['passed']and rec['complete_proof']['passed'];assert rec['rtl_sha256']==sha(D/'candidates'/k/'block_v1_r.sv')
 manifests={c['path']:c['sha256']for c in load(D/'evidence/attempt003/results/corpus/MANIFEST.json')['cases']}
 manifests.update({c['path']:c['sha256']for c in load(E/'attempt027/results/corpus/MANIFEST.json')['cases']})
 raw=[];counts={}
 for n,expected in [(15,756),(22,552),(27,12),(38,126),(45,94),(53,336)]:
  rr=load(E/f'attempt{n:03d}/results/RESULTS.json');assert len(rr)==expected,(n,len(rr));assert all(r['exit']==0 for r in rr)
  for r in rr:
   assert r['input_sha256']==manifests[r['workload']]
   if r['status']!='PASS':assert r['status']=='UNSUPPORTED_ORIGINAL_CAPACITY'and r['architecture']==0 and r['workload'].startswith('W2')
   else:assert r['S_allocated_peak']<=16384 and r['max_outstanding_writes']<=1 and r['cycles']<=sum(r['stages'].values())
  counts[n]=len(rr);raw+=rr
 with(D/'SYSTEMC_RESULTS.csv').open(encoding='utf-8-sig')as f:rows=list(csv.DictReader(f))
 assert len(rows)==len(raw)==1876;assert sum(r['status']=='PASS'for r in rows)==1836;assert sum(r['status']=='UNSUPPORTED_ORIGINAL_CAPACITY'for r in rows)==40
 for p in(R/'project/experiments/r_architecture').glob('*.py'):ast.parse(p.read_text(encoding='utf-8'))
 b=load(E/'PHYSICAL_METRICS_SNAPSHOT.json')['B256'];assert b['flow_receipt']['exit']==0;assert b['metrics']['5_2_route.json']['detailedroute__route__drc_errors']==0
 assert b['metrics']['6_report.json']['finish__timing__setup__ws']<0 and b['metrics']['6_report.json']['finish__timing__hold__ws']<0
 result=dict(passed=True,scope='evidence identity, complete proof certificates and measured accounting; not physical signoff',systemc_rows=len(rows),systemc_pass=1836,unsupported=40,counts=counts,full_equivalence=['A1','A2h'],state_plus_output_bits=146269,partitions_each=772,original_evidence_unchanged=True)
 (D/'VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
