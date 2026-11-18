from pathlib import Path
import json,hashlib
R=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');run=R/'cu/runs/C-v43-margin-plan0';res=run/'flow/results/nangate45/c-overlay-current/base';p=Path.cwd()
def h(f):
    d=hashlib.sha256()
    with Path(f).open('rb') as s:
        for b in iter(lambda:s.read(1024*1024),b''):d.update(b)
    return d.hexdigest()
assert h(run/'candidate.sha256')=='856f73f4489fc64ce3a8d20f3995aa18ee1736deb081f756ee18769bfbff3c4a'
assert 'case_complete=true' in (run/'CANDIDATE-COMPLETE.txt').read_text()
files={}
for name in ['candidate.sha256','prepared.sha256','inputs.sha256']:
    f=run/name;files[str(f)]=h(f)
    for line in f.read_text().splitlines():
        digest,filename=line.split(None,1);source=Path(filename.strip().lstrip('*'))
        if not source.is_absolute():source=run/source
        assert h(source)==digest,source
        files[str(source)]=digest
actual=p/'fresh-from-odb.v';assert h(actual)==h(res/'6_final.v')=='2b74fbc9009a57b54f177c89a929a08abfadff7f566ed56928b0ce1441606e77'
catalog=R/'audit/C-fixture-catalog-v2.json';assert h(catalog)=='b8c47e99669b7c9069ad9369301d406ef788af3b0abd78e297bf2a2765bfc963'
for f in [run/'CANDIDATE-COMPLETE.txt',catalog,run/'config.mk',actual,p/'export.log',p/'export.tcl',Path(__file__)]:files[str(f)]=h(f)
prior=R/'audit/C43-plan0-prepared/proof/complete-equivalence-receipt.json';assert json.loads(prior.read_text())['passed'];files[str(prior)]=h(prior)
(p/'actual-export-binding.json').write_text(json.dumps(dict(export_verified=True,saved_final_verilog_exact=True,common_legalized_byte_identical=False,requires_actual_final_strict_proof=True,physical_acceptance=False,hashes=files),indent=2)+'\n')
files[str(p/'actual-export-binding.json')]=h(p/'actual-export-binding.json')
manifest=dict(gate=str(actual),odb=str(res/'6_final.odb'),config=str(run/'config.mk'),provenance=str(run/'candidate.sha256'),fixture_catalog=str(catalog),expected_sha256=files)
(p/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('ACTUAL_C43_FINAL_EXPORT_EXACT_SAVED_VERILOG')
