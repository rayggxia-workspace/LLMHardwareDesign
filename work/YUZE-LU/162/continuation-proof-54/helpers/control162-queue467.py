from pathlib import Path
import subprocess,shlex
h=Path(__file__).parent;q=(h/'control162-queue466-remote.py').read_text(encoding='utf-8')
q=q.replace('sready466-padding-full-upper','sready467-padding-full-upper').replace("[(4660,8,'dynamic-05/node2'),(4661,2,'dynamic-04/node25')]","[(4670,8,'dynamic-05/node4')]")
q=q.replace('cap-candidates/4610','cap-candidates/4611').replace('cap-necessary-461/4610','cap-necessary-461/4611').replace('placement=4610','placement=4611').replace("replace('sready434','sready466')","replace('sready434','sready467')")
q=q.replace('chains4660/4661 use actual4610','chain4670 uses actual4611').replace('Costs8/2','Cost8').replace('Node2 native slot and node25 placement slot naturally refill','Node4 completed placement slot naturally refills')
compile(q,'queue467','exec');(h/'control162-queue467-remote.py').write_bytes(q.encode());print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
