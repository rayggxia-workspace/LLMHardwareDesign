"""Correctly separate a truncated DRC detail report from the complete log counts."""
from pathlib import Path
import json,subprocess,shlex,hashlib

home=Path(r'D:\Data\电路实验');old=home/'control162-short-diagnostic182.json';d=json.loads(old.read_text())
q=r'''from pathlib import Path
import json,re,hashlib
p=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/router-full-cugr-snapshot-181/openroad.log');raw=p.read_bytes();s=raw.decode();matches=list(re.finditer(r'Number of violations = (\d+)\.\nViol/Layer[^\n]*\n((?:[^\n]*\n){4})',s));assert matches
m=matches[-1];rows={}
for line in m.group(2).splitlines():
 tokens=line.split();assert len(tokens)>=4;rows[' '.join(tokens[:-3])]=dict(zip(['metal11','via11','metal12'],map(int,tokens[-3:])))
assert sum(sum(v.values())for v in rows.values())==int(m.group(1))
print(json.dumps(dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),actual_last_iteration_violations=int(m.group(1)),actual_last_iteration_types=rows)))
'''
r=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45));assert r['actual_last_iteration_violations']>d['total_violations']
d['raw_detail_records']=d.pop('total_violations');d['complete_actual_log']=r;d['detail_coverage_fraction']=d['raw_detail_records']/r['actual_last_iteration_violations'];d['detail_is_complete']=False;d['detail_bias_warning']='Detail output contains exactly10000 Short and10000 Metal Spacing records, while complete actual log counts are much larger. Report is truncated/ordered; its driver and spatial counts are NOT estimates of the full population.'
d['scope']='Completed bounded replay diagnostic, not qualification. All23620 emitted3-line detail records parsed, but complete actual log has950442 violations. Keep exact raw record counts separate from full iteration counts. Driver pairs/spatial bins characterize ONLY this ordered truncated detail report; do not infer a dominant global cause from it. Supersedes ambiguous total_violations field in182 without overwriting the original derived artifact.'
d['supersedes_sha256']=hashlib.sha256(old.read_bytes()).hexdigest();out=home/'control162-short-diagnostic183.json';assert not out.exists();out.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:d[k]for k in ['raw_detail_records','complete_actual_log','detail_coverage_fraction','detail_is_complete','detail_bias_warning']}))
