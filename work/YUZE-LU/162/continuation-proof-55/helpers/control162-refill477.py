from pathlib import Path
import subprocess,shlex
h=Path(__file__).parent;q=(h/'control162-refill415-remote.py').read_text(encoding='utf-8')
q=q.replace('sready415-channel-placement-refill','sready477-controlled-weight-refill').replace('sready414-routing-channel-placement','sready476-controlled-high-weight').replace("len(tasks['tasks'])==6","len(tasks['tasks'])==8")
q=q.replace("[(3,95098,'dynamic-02/node3',2231),(25,95204,'dynamic-04/node25',1853)]","[(7,96297,'dynamic-07/node7',3930)]")
q=q.replace("len(g['instances'])==235 and 'macro_r'not in g['instances']","len(g['instances'])==345 and 'macro_r'in g['instances']")
q=q.replace("assert logs\n", """assert logs
 assert source.name=='source-388'
 attempts=[]
 for f in Path(out).glob('trial-*/router.log'):
  lines=f.read_text().splitlines();failed=bool(lines and not lines[-1].startswith('{'))
  attempts.append(dict(path=str(f),sha256=sha(f),failed_message=lines[-1]if failed else None))
 assert len(attempts)==16 and sum(r['failed_message']is not None for r in attempts)>=8
""")
q=q.replace('logs=logs,whole_system_qualified=False','logs=logs,prior_attempts=attempts,whole_system_qualified=False')
q=q.replace('Replace exactly one verified own obsolete235-instance no-R duplicate search on each node with current345instance reset53 exact-density routing-channel placements. New two placement searches and per-placement actual native/pin necessary successors queued first. Existing current full searches remain active; only obsolete no-R235 own duplicates replaced.','Replace exactly one verified own current359 older-source388 search3930 after at least8/16 attempts failed without dynamic refill, leaving reserved cores idle. Actual logs/individual SHA retained, not a claim remaining searches cannot succeed. New actual475 high-weight preflight plus controlled4760 full7stage candidate453 chain queued first, same placement4610/RNG4661 as4661 and all final gates. New candidate is not accepted; all other current full searches remain active.')
compile(q,'refill477','exec');(h/'control162-refill477-remote.py').write_bytes(q.encode());print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
