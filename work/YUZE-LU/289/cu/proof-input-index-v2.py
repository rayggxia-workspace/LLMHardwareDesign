from pathlib import Path
import hashlib,json
p=Path(__file__).parent
names=['loader-original.sv','loader-parallel.sv','loader-arithmetic.sv','select-gold.sv','select-gate.sv','select-proof.ys','select-proof-recovery.log','div3-proof.sv','div3-proof.ys','div3-proof.log','div3-exhaustive.json','compositional-obligations.json']
r={'scope':'Stable two-state hardware values with defined reset/state semantics; not four-state X/event equivalence. Whole-module SAT result is separate.','supersedes_hash_interpretation':'Old original_sha256/parallel_sha256 in obligations are normalized text hashes, not raw file hashes. Old receipt preserved.','files':{}}
for n in names:
 f=p/n
 if f.exists():
  r['files'][n]={'raw_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'normalized_text_sha256':hashlib.sha256(f.read_text().encode()).hexdigest(),'bytes':f.stat().st_size}
(p/'proof-input-index-v2.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r))
