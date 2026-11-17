"""Package only report deliverables; never include transport helpers or dependencies."""
import csv
from hashlib import sha256
import json
from pathlib import Path
import zipfile

root=Path(__file__).resolve().parent
data=json.loads((root/'seven-model-speed-results.json').read_text(encoding='utf-8'))
fields=['model','name','short_prefill_input_tok_s','short_prefill_ms','estimated_prefill_body_s',
        'estimated_prefill_to_logits_s','estimated_input_tok_s_to_logits','decode_tok_s',
        'component_max_deviation_percent','nonlinear_screen_exceeded','independent_sequence_validation']
with (root/'seven-model-speed-summary.csv').open('w',encoding='utf-8-sig',newline='') as stream:
    writer=csv.DictWriter(stream,fieldnames=fields)
    writer.writeheader()
    writer.writerows({k:r[k] for k in fields} for r in data['models'].values())
names=['README.md','sample_context.py','run_context_samples.sbatch','build_speed_report.py',
       'verify_report.py','package_report.py','seven-model-speed-report.html',
       'seven-model-speed-results.json','seven-model-speed-summary.csv','report-checks.json']
paths=[root/n for n in names]+sorted((root/'inputs').glob('*.json'))+sorted((root/'results').glob('*/*json'))
paths += [root/'results'/n for n in ['jobs-final.txt','server-results.sha256','scripts-final.sha256']]
manifest={str(p.relative_to(root)).replace('\\','/'):sha256(p.read_bytes()).hexdigest() for p in paths}
(root/'SHA256SUMS.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
paths.append(root/'SHA256SUMS.json')
target=root/'seven-model-speed-report.zip'
with zipfile.ZipFile(str(target),'w',zipfile.ZIP_DEFLATED) as archive:
    for p in paths:
        archive.write(str(p),str(p.relative_to(root)))
with zipfile.ZipFile(str(target)) as archive:
    assert archive.testzip() is None
    assert all(not name.startswith('.') for name in archive.namelist())
    for name,value in manifest.items():
        assert sha256(archive.read(name)).hexdigest()==value
print(json.dumps(dict(file=str(target),bytes=target.stat().st_size,files=len(paths),sha256=sha256(target.read_bytes()).hexdigest())))
