from pathlib import Path
import hashlib,json,re
p=Path(__file__).parent
rows=[]
for d in sorted(p.glob('loader-phys2-*')):
 if not (d/'setup.rpt').exists():continue
 kind,util=d.name[len('loader-phys2-'):].rsplit('-u',1)
 source=p/f'loader-{kind}.sv'
 log=(d/'physical.log').read_text()
 rows.append({'candidate':kind,'util_percent':int(util),'setup_slack_ns':float(re.search(r'worst slack max ([\d.-]+)',(d/'setup.rpt').read_text())[1]),'source_raw_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'physical_log_raw_sha256':hashlib.sha256((d/'physical.log').read_bytes()).hexdigest(),'completed': 'Design area' in log and (d/'placed.odb').exists()})
(p/'loader-physical-comparison.json').write_text(json.dumps({'scope':'Same mapped-netlist method, clock4ns, IO0.2/0.8ns, input BUF_X2 source50ps, output2fF, utilization30/50%, place+repair_design+repair_timing+legalize+placement-RC. Module diagnostics, NOT full C postroute signoff. No fixed absolute die size across candidates.','candidates':rows},indent=2)+'\n')
print(json.dumps(rows))
