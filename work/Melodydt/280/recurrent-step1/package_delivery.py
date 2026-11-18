"""Create and verify a portable first-round data/code bundle without gate waveforms."""
from pathlib import Path
from hashlib import sha256
import json,zipfile,subprocess,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
OUT=ROOT/'output/pdf/seven-model-sync/2026-11-18-r4'
pdf=OUT/'recurrent-state-first-round.pdf'
assert pdf.is_file() and (HERE/'rollup-check.json').is_file()
files=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='public-files.json']
files += [ROOT/'work/Melodydt/280'/f for f in ['verify_arithmetic_capture.py','verify_operator_capture.py',
          'seven_model_arithmetic_estimate.py','six_model_tlm_power.py',
          'qwen35_tlm_power_v3_arithmetic.json','falcon_tlm_power_v3_arithmetic.json']]
files += list((ROOT/'work/Melodydt/280/arithmetic-calibration-results').glob('*-calibration.json'))
files += [ROOT/'tmp/recurrent-step1'/f'{m}-{p}.json' for m in ('qwen35','falcon') for p in ('prefill','decode')]
files += [ROOT/'tmp/recurrent-step1'/(m+'-cal')/f for m in ('qwen35','falcon-wide') for f in ('commands.txt','segments.json')]
files += [pdf,OUT/'receipt.json']
files += [OUT/'200mhz-power.pdf',OUT/'combined-receipt.json']
files += [ROOT/'docs/handoffs/2026-11-18-issue-280-recurrent-first-round.md']
files += [ROOT/'output/pdf/seven-model-sync/2026-11-18-r3'/f for f in ('200mhz-power.pdf','sync-receipt.json')]
files=sorted(set(files))
manifest={p.relative_to(ROOT).as_posix():sha256(p.read_bytes()).hexdigest() for p in files}
archive=OUT/'recurrent-state-first-round-bundle.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in files:
        info=zipfile.ZipInfo(p.relative_to(ROOT).as_posix(),(2026,11,18,0,0,0))
        info.compress_type=zipfile.ZIP_DEFLATED
        z.writestr(info,p.read_bytes(),compresslevel=9)
    z.writestr('MANIFEST.sha256.json',json.dumps(manifest,indent=2)+'\n')
    z.writestr('BUNDLE-README.txt','Extract into an empty directory. Run Python work/Melodydt/280/recurrent-step1/rollup_candidate.py and verify_candidate.py to reproduce the conditional model rollup. See DELIVERY.md and README.md in that directory for source, jobs, limits and RTL replay. Gate netlists and large VCD remain at the documented project server paths. This archive includes genuine captures, exact gate commands, pinned RTL and all data required by the rollup. NumPy is needed for numerical replay; ReportLab/pypdf and Windows Deng fonts for PDF generation. No credentials are included.\n')
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for name,h in manifest.items():assert sha256(z.read(name)).hexdigest()==h,name
    extracted=ROOT/('tmp/recurrent-step1/package-check-'+sha256(archive.read_bytes()).hexdigest()[:12])
    assert not extracted.exists(),'use a fresh package-check directory'
    z.extractall(extracted)
for script in ('rollup_candidate.py','verify_candidate.py'):
    subprocess.run([sys.executable,'-B',str(extracted/'work/Melodydt/280/recurrent-step1'/script)],check=True)
assert (extracted/'work/Melodydt/280/recurrent-step1/candidate-rollup.json').read_bytes()==(HERE/'candidate-rollup.json').read_bytes()
(OUT/'bundle-receipt.json').write_text(json.dumps(dict(zip_sha256=sha256(archive.read_bytes()).hexdigest(),
    zip_bytes=archive.stat().st_size,files=len(manifest),member_sha256_pass=True,isolated_rollup_pass=True),indent=2)+'\n')
print('PORTABLE_BUNDLE_PASS',archive,len(manifest))
