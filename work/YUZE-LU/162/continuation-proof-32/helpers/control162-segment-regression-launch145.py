"""Use one exact own duplicate search slot for a full equivalence regression."""
from pathlib import Path
import ast,subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-regression-launch142.py');q=ast.literal_eval(ast.parse(p.read_text(encoding='utf-8')).body[1].value)
changes={"source=b/'source-142'":"source=b/'source-145'",'415069fbe00e9706eee8bfcfeec842ec4b0ac878':'4c662be28f361e1cfeb363f95096d7c7e6397b30','sready142-independent-congestion-regression':'sready145-segment-regression','dynamic-05/node4':'dynamic-02/node26','1411':'1454','1410':'1453',"+1]=='4'":"+1]=='1'",'95391':'95119','node4':'node26','router-congestion-regression-01':'router-segment-regression-01','00-r-sready142-search-regression':'00-r-sready145-segment-regression',
 'Retire one exact own slow coupled-weight4 ordering search to admit full default-plus-new search-order regression; preserve all old evidence, other search controls, parent allocations and physical gates. Not a completed physical failure.':'Retire only verified own duplicate original weight1 search1454 to run full136-case segment-distance regression and compare every existing140 successful route output exactly to source144. Preserve other original/cached/product searches, all parent allocations, immutable specs/partial results, other tasks/R and all physical acceptance gates. Incomplete search retirement, not physical failure; no real source145 scene admitted before exact comparison passes.'}
for old,new in changes.items():assert old in q,old;q=q.replace(old,new)
compile(q,'actual_segment_regression','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55).decode())
