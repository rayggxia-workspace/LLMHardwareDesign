from pathlib import Path
import re,json,hashlib
p=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v27-rcx-normalization-v2/reextract-encoder');active=False;count=0;rails=[];name=None
for line in (p/'before.def').open():
 if re.match(r'^NETS\s+\d+\s*;',line):active=True;continue
 if not active:continue
 if line.strip()=='END NETS':break
 m=re.match(r'^\s*-\s+(\S+)\s',line)
 if m:name=m[1];count+=1
 if re.search(r'\+\s+USE\s+(POWER|GROUND)\b',line):rails.append(name)
assert count==275054 and sorted(rails)==['VDD','VSS']
v=dict(qualification_receipt_sha256=hashlib.sha256((p/'receipt.json').read_bytes()).hexdigest(),net_declarations_checked=count,signal_and_clock_nets=count-len(rails),duplicate_unrouted_power_NETS_declarations=rails,scope_note='Legacy receipt field signal_nets counts all checked NETS declarations, including these two empty power declarations. Read its value275054 as net_declarations_checked; actual signal/clock count is275052. Geometry/PG qualification is unchanged; original receipt preserved.')
(p/'count-scope-clarification.json').write_text(json.dumps(v,indent=2));print(json.dumps(v,indent=2))
