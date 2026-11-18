"""Package small, qualified evidence; exclude raw physical and model payloads."""
from hashlib import sha256
import json
from pathlib import Path
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]

def digest(p):return sha256(p.read_bytes()).hexdigest()

def main():
    files=set()
    for pattern in ('*.py','*.sbatch','*.sv','*-source-commit.txt','*-inputs.sha256'):
        files.update(HERE.glob(pattern))
    selected=['README.md','control-periphery-calibration.json','control-periphery-cut-bindings.json',
        'control-periphery-results.sha256','conv4-pin-calibration.json','conv4-pin-results.sha256',
        'special-pin-calibration.json','special-pin-results.sha256','dma-coefficients.json',
        'e32-retry-jobs.json','cal-jobs.txt','deployments-current.tar.gz','deployments-current.tar.json',
        'pdf-progress-validation.json','integrated-ledger-validation.json']
    files.update(HERE/n for n in selected)
    for pattern in ('dma-*-pin-calibration.json','dma-*-pin-results.sha256','dma-*-boundary.json'):
        files.update(HERE.glob(pattern))
    for directory in ('deployment-audits','timing-ledger','dma-ledger','special-candidate-ledger'):
        files.update((HERE/directory).glob('*.json'))
    files.update([ROOT/'docs/handoffs/2026-11-18-issue-280-closure-v5.md',
                  ROOT/'docs/experiments/seven-model-energy-evaluation.pdf',
                  ROOT/'docs/experiments/seven-model-energy-evaluation-v4.pdf'])
    assert all(p.is_file() for p in files)
    rows=[dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=digest(p)) for p in sorted(files)]
    manifest=dict(scope='Qualified partial v5 evidence and continuation scripts; three requested items are not fully accepted',
        owner='Melodydt',issue=280,pull_request=281,branch='task/280-seven-model-energy',
        baseline_report_sha256=digest(ROOT/'docs/experiments/seven-model-energy-evaluation-v4.pdf'),
        raw_data_location='BSCC ~/LLMHardware/zenanyan/issue-280-bscc-t6-01; exact subdirectories and accepted manifests in handoff',
        excluded=['model weights/history payloads','raw C639 source and full traces','mapped physical databases and 1GB pin graphs','credentials'],
        limits=['Requires authorized server artifact access to rerun hardware calibration',
                'Included deployments-current.tar.gz holds only accepted small JSON outputs, not raw model/physical data',
                'Candidate fixed-point samples and partial activity propagation do not establish complete-model RTL/physical acceptance'],
        files=rows)
    index=HERE/'review-pack-manifest.json';index.write_text(json.dumps(manifest,indent=2)+'\n')
    dest=HERE/'closure-v5-review-pack.zip'
    with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(files|{index}):z.write(p,p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(dest) as z:
        assert z.testzip() is None
        for row in rows:assert sha256(z.read(row['path'])).hexdigest()==row['sha256']
    (HERE/'review-pack.sha256').write_text(digest(dest)+'  '+dest.name+'\n')
    print('REVIEW_PACK_PASS',len(rows),'files',dest.stat().st_size,'bytes',digest(dest))

if __name__=='__main__':main()
