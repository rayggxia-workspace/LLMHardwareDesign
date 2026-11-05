from pathlib import Path
import subprocess,shlex,re
h=Path(__file__).parent;q=(h/'control162-refill520-remote.py').read_text(encoding='utf-8')
q=q.replace('sready520-failed-pool-grid-refill','sready527-progressive-window-refill').replace('sready519-ordinary-cost-grid','sready525-progressive-search-window').replace("len(tasks['tasks'])==21","len(tasks['tasks'])==8")
q=re.sub(r'for node,job,folder,seed,expected_source,minimum_failed in \[.*\]:',"for node,job,folder,seed,expected_source,minimum_failed in [(3,95098,'dynamic-02/node3',3731,'source-358',4)]:",q,count=1)
start='Replace exactly one verified own older-source359 fixed16-attempt search per listed node after5/7/7 attempts actually exited and no dynamic refill exists.'
q=q.replace(start,'Replace exactly one verified own older-source358 current359 fixed16-attempt3731 search after at least4 actual exited trials and no dynamic refill exists.')
q=q.replace('three complete7stage source510 candidates complete the two qualified placements by two tested ordinary-cost grid alongside5120, with all original final gates unchanged.','one source524 progressive ordinary search-window preflight and controlled5260 complete7stage candidate queued first; all original physical gates and finite-resource branch unchanged. This tests a software search-locality hypothesis only, not global infeasibility.')
compile(q,'refill527','exec');(h/'control162-refill527-remote.py').write_bytes(q.encode());print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
