from pathlib import Path
import subprocess,shlex
h=Path(__file__).parent;q=(h/'control162-refill463-remote.py').read_text(encoding='utf-8').replace('sready463-padding-placement-refill','sready464-padding-placement-refill')
q=q.replace("Path(out)/'trial-0/router.log'","Path(out)/'trial-0/router.log',Path(out)/'openroad-search/case-0/openroad.log'")
prefix="""from pathlib import Path
import json,time
prior=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/route-selection-102/sready463-padding-placement-refill');assert prior.exists()and not(prior/'failure.json').exists();(prior/'failure.json').write_text(json.dumps(dict(captured_at=time.time(),passed=False,observed_failure='AssertionError at line27 assert logs: old1840 is CUGR and actual log is openroad-search/case-0/openroad.log, not router.log or trial-0/router.log',raw_stderr_captured_as_file=False,cancel_was_not_reached=True,scope='Exact identity guards passed before bounded log path assertion. No cancellation occurred; preserve original source/replacement. Corrected464 includes actual existing CUGR log and repeats all identity checks.')))
"""
q=prefix+q;compile(q,'refill464','exec');(h/'control162-refill464-remote.py').write_bytes(q.encode());print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
