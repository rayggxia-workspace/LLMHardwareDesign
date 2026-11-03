"""Prepare actual halo routes only after executed zero-violation bounds.

Reuses the existing immutable-source queue/acceptance implementation. Running
without --submit prints the generated remote program and makes no server call.
"""
import subprocess
import shlex
import sys
from pathlib import Path

parent = Path(r'D:\Data\电路实验\control162-independent-route142.py')
scope = {}
exec(compile(parent.read_text(encoding='utf-8').rsplit('\nprint(subprocess.check_output', 1)[0], str(parent), 'exec'), scope)
q = scope['q']
changes = {
    's-ready-congestion-source142.json': 's-ready-halo-routes-source142.json',
    "residual=base/'capacity-native-residual-01'": "residual=base/'halo-native-residual-01'",
    "base/'native-pin-load-01": "base/'halo-native-pin-load-01",
    "pd=json.loads((base/'halo-native-pin-load-01/native-pin-load.json').read_text());assert not any(next(r for r in pd['placements']if Path(r['placement']).name=='1424')['violations'].values());required_base.append(pin_receipt)":
    "pd=json.loads((base/'halo-native-pin-load-01/native-pin-load.json').read_text());pin_valid={int(Path(r['placement']).name)for r in pd['placements']if not any(r['violations'].values())};options=[row for row in options if int(row[3].name)in pin_valid];required_base.extend([pin_receipt,base/'final-composition/receipt.json']);assert json.loads((base/'final-composition/receipt.json').read_text())['passed']\nif not options:print('No actual halo cleared native RC plus real input pin loads; no route admitted');raise SystemExit(0)",
    'options=[(1460,4,4,valid[1424])]': "options=[(1480+n-1470,5,4,p)for n,p in sorted(valid.items())if n in (1470,1471,1472)]\nif not options:print('No actual halo passed every necessary bound; no route admitted');raise SystemExit(0)",
    'assert node in (2,3,4,6)': 'assert node==5',
    "(('dynamic-05/'if node in (2,4)else'dynamic-02/')+'node'+str(node))": "('dynamic-03/node5')",
    'sready140-': 'sready142halo-',
    'One independent decoupled-congestion search on the exact pin-bound-cleared1424 placement and6 complete downstream gates; new128-case actual router regression required; all physical gates exactly unchanged':
    'Actual externally expanded halo scenes with all native relative placements fixed; each scene requires executed native-ground plus actual minimum final-ODB input-load bounds clear at all three corners and actual selected1391 function pass. Independent real routes and six complete downstream gates per scene; actual area charged and all physical acceptance unchanged',
}
for old, new in changes.items():
    assert old in q, old
    q = q.replace(old, new)
# The original1471/1472 steps failed in Slurm before EDA; unique1473/1474
# and bound02 retain their failures and use exactly the same hardware.
q=q.replace('halo-native-residual-01','halo-native-residual-02').replace('halo-native-pin-load-01','halo-native-pin-load-02')
q=q.replace('options=[(1480+n-1470,5,4,p)for n,p in sorted(valid.items())if n in (1470,1471,1472)]',
            'options=[(seed,5,4,valid[n])for seed,n in [(1480,1470),(1481,1473),(1482,1474)]if n in valid]')
anchor="residual=base/'halo-native-residual-02'"
preflight="""for actual in [base/'halo-native-residual-02/receipt.json',base/'halo-native-pin-load-02/receipt.json',base/'final-composition/receipt.json']:
 if not actual.exists():print('Actual halo prerequisites unfinished; no route admitted:',actual);raise SystemExit(0)
 assert json.loads(actual.read_text())['passed'],str(actual)
"""
assert anchor in q
q=q.replace(anchor,preflight+anchor,1)
assert "valid[1424]" not in q
assert "source=b/'source-142'" in q
compile(q, 'actual_halo_routes_and_unchanged_acceptance', 'exec')
if '--submit' in sys.argv:
    result = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                             'yuzelu@10.129.166.172', 'python3 -c ' + shlex.quote(q)],
                            capture_output=True, text=True, timeout=45)
    print(result.stdout)
    print(result.stderr, file=sys.stderr)
    raise SystemExit(result.returncode)
print(q)
