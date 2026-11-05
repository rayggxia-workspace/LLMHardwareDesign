from pathlib import Path
import subprocess,shlex
h=Path(__file__).parent;q=(h/'control162-queue419-remote.py').read_text(encoding='utf-8')
q=q.replace("root=b/'r256-composition-359';source=b/'source-411'","root=b/'r256-composition-453';old=b/'r256-composition-359';source=b/'source-451'")
q=q.replace('sready419-balanced-density-placement','sready461-padding-native-aware-placement').replace("pin=root/'native-pin-load369';assert json.loads((pin/'receipt.json').read_text())['passed']","pin=root/'native-pin-load'")
q=q.replace("root/'selected/physical.json'","old/'selected/physical.json'").replace("root/'fixed-pg-wrappers'","old/'fixed-pg-wrappers'")
q=q.replace("[(4190,64,10000000,'dynamic-05/node4'),(4191,64,100000000,'dynamic-03/node5')]","[(4610,64,1000000,'dynamic-04/node25'),(4611,64,10000000,'dynamic-05/node4')]")
q=q.replace('sready419','sready461').replace('cap-necessary-419','cap-necessary-461')
a=q.index("scope='Existing exact-density");e=q.index("'),indent=2",a)
q=q[:a]+"scope='Candidate453: same23 fixed macros and345 state owners, only267 proven unconsumed Link8 inputs moved from payload to their existing reset banks; actual native/current program requalification still running. Two existing exact-density searches weight1e6/1e7 gap64 wait for actual new native-ground/minimum-pin report, then independent placement/residual/pin successors. Added reset pin loads all counted. No route launched without inspecting new necessary reports; no old graph or function qualification inheritance. Original final geometry/PG/threeRC300MHz/actualprogram/joint gates and actual memory gate unchanged. Node25 natural vacant slot after completed initial placement, node4 original diagnostic retained until genuine new dependency readiness.'"+q[e+1:]
compile(q,'queue461','exec');(h/'control162-queue461-remote.py').write_bytes(q.encode());print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
