from pathlib import Path
import subprocess,shlex
h=Path(__file__).parent;q=(h/'control162-refill415-remote.py').read_text()
q=q.replace('sready415-channel-placement-refill','sready440-critical-priority-refill').replace('sready414-routing-channel-placement','sready439-critical-first').replace("len(tasks['tasks'])==6","len(tasks['tasks'])==8")
q=q.replace("[(3,95098,'dynamic-02/node3',2231),(25,95204,'dynamic-04/node25',1853)]","[(3,95098,'dynamic-02/node3',2232)]")
q=q.replace('Replace exactly one verified own obsolete235-instance no-R duplicate search on each node with current345instance reset53 exact-density routing-channel placements. New two placement searches and per-placement actual native/pin necessary successors queued first.','Replace exactly one verified own obsolete235-instance no-R duplicate search on node3 with current345instance reset53 controlled constrained-priority comparison. New438 regression and4390 full7stage chain queued first, same RNG4340 and placement4240 as baseline4340.')
compile(q,'refill440','exec');(h/'control162-refill440-remote.py').write_bytes(q.encode());print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
