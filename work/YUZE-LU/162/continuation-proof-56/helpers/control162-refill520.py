from pathlib import Path
import subprocess,shlex
h=Path(__file__).parent;q=(h/'control162-refill415-remote.py').read_text(encoding='utf-8')
q=q.replace('sready415-channel-placement-refill','sready520-failed-pool-grid-refill').replace('sready414-routing-channel-placement','sready519-ordinary-cost-grid').replace("len(tasks['tasks'])==6","len(tasks['tasks'])==21")
q=q.replace("for node,job,folder,seed in [(3,95098,'dynamic-02/node3',2231),(25,95204,'dynamic-04/node25',1853)]:","for node,job,folder,seed,expected_source,minimum_failed in [(2,95341,'dynamic-05/node2',3890,'source-388',5),(3,95098,'dynamic-02/node3',3891,'source-388',7),(25,95204,'dynamic-04/node25',3841,'source-383',7)]:")
q=q.replace("len(g['instances'])==235 and 'macro_r'not in g['instances']","len(g['instances'])==345 and 'macro_r'in g['instances']")
q=q.replace('assert logs\n',"""assert logs
 assert source.name==expected_source and graph==current and '--route-trial-attempts'not in a
 assert json.loads((b/'r256-padding-final-function-audit-472/receipt.json').read_text())['passed']and json.loads((b/'r256-ordinary-cost-regression-511/receipt.json').read_text())['passed']
 attempts=[]
 for f in Path(out).glob('trial-*/router.log'):
  lines=f.read_text().splitlines();last=lines[-1]if lines else '';failed=last.startswith(('Locked-source optimistic wire budget exceeded by this search:','disconnected tree:','disconnected finite-resource tree:'))
  attempts.append(dict(path=str(f),sha256=sha(f),failed_message=last if failed else None))
 assert len(attempts)==16 and sum(r['failed_message']is not None for r in attempts)>=minimum_failed
""")
q=q.replace('logs=logs,whole_system_qualified=False','logs=logs,prior_attempts=attempts,whole_system_qualified=False')
q=q.replace('Replace exactly one verified own obsolete235-instance no-R duplicate search on each node with current345instance reset53 exact-density routing-channel placements. New two placement searches and per-placement actual native/pin necessary successors queued first. Existing current full searches remain active; only obsolete no-R235 own duplicates replaced.','Replace exactly one verified own older-source359 fixed16-attempt search per listed node after5/7/7 attempts actually exited and no dynamic refill exists. Preserve every failed/surviving log SHA and partial output; no remaining-trial infeasibility claim. Actual453 real programs and511 new search preflight passed; three complete7stage source510 candidates complete the two qualified placements by two tested ordinary-cost grid alongside5120, with all original final gates unchanged. Restore16active trials with finite64-attempt dynamic refill, no concurrency reduction. Only listed exact owned steps replaced; all other current searches and foreign/R tasks stay untouched.')
q=q.replace("print('refilled obsolete own search'","print('refilled verified own partial pool'")
compile(q,'refill520','exec');(h/'control162-refill520-remote.py').write_bytes(q.encode());print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
