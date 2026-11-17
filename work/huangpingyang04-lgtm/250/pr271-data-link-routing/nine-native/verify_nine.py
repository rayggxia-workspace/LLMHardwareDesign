"""Independent checks on the nine-base release, including source-native contacts."""
from pathlib import Path
from itertools import combinations
from collections import Counter
import csv,gzip,hashlib,json,sys
root=Path(__file__).resolve().parent;case=root/'final';sys.path.insert(0,str(root/'engine'))
from check import verify
from geometry import Occupancy,contains,too_close
def content(p):return p.read_bytes() if p.exists() else gzip.decompress(p.with_suffix(p.suffix+'.gz').read_bytes())
def load(p):return json.loads(content(p))
def sha(p):return hashlib.sha256(content(p)).hexdigest()
spec=load(case/'spec.json');route=load(case/'route.json');place=load(case/'placement.json');checks=load(case/'checks.json')
assert verify(spec,route)==checks and checks['nets_checked']==1049 and checks['via10_count']==2102
assert not route['failed']
boxes=place['boxes_dbu'];assert set(boxes)=={'P0','P1','P2','C0','U0','U1','F0','J0','J1'}
assert not place['standalone_reader_blocks'] and not place['peripheral_blocks']
assert all(not too_close(a,b,0) for a,b in combinations(boxes.values(),2))
assert spec['technology']['bounds']==place['bounds_dbu']
assert spec['context']['placement_sha256']==sha(case/'placement.json')
assert spec['context']['lower_overlay_sha256']==sha(case/'lower-overlay.json')
for pin,rects in spec['pins'].items():
 block=pin.split('.')[0];assert block in boxes
 for b in rects:
  assert all(not too_close(b,r,0) for other,r in boxes.items() if other!=block),(pin,'foreign base overlap')
for pin,shapes in load(case/'lower-overlay.json')['by_terminal'].items():
 for layer,b in shapes:
  assert all(not too_close(b,r,0) for other,r in boxes.items() if other!=pin.split('.')[0]),(pin,'lower adapter overlaps foreign base')
rows=list(csv.DictReader((case/'connections.csv').open()))
assert len(rows)==1053
assert {(r['net'],r['driver'],r['sink']) for r in rows}=={(n['id'],n['driver'],s) for n in spec['nets'] for s in n['sinks']}
assert {r['status'] for r in rows}=={'upper_geometry_checked'}
expected=load(case/'native-expected-contacts.json');proof=load(case/'native-provenance.json')
for key,block,total in [('C','C0',512),('P2','P2',412)]:
 folder=case/('native-'+key);ports={};owners={};directions={}
 assert sha(folder/'ports.tsv')==proof[key]['ports_sha256']
 assert sha(folder/'native.tsv.gz')==proof[key]['geometry_sha256']
 for r in csv.reader((folder/'ports.tsv').open(),delimiter='\t'):
  if r[0]=='term':owners[r[1]]=r[4];directions[r[1]]=r[2]
  if r[0]=='pin' and r[2]=='metal10':ports.setdefault(r[1],[]).append(list(map(int,r[3:])))
 occ=Occupancy(spec['technology'])
 with gzip.open(folder/'native.tsv.gz','rt') as f:
  for line in f:
   if line.startswith('#'):continue
   owner,layer,role,*b=line.split()
   if layer=='metal10':occ.add([('M10',list(map(int,b)))],owner)
 count=0
 for pin,b in expected.items():
  if not pin.startswith(block+'.'):continue
  name=pin.split('.',1)[1];assert b in ports[name];count+=1
  assert contains([0,0,boxes[block][2]-boxes[block][0],boxes[block][3]-boxes[block][1]],b)
  query=[b[0]-3000,b[1]-3000,b[2]+3000,b[3]+3000]
  assert all(o==owners[name] or not too_close(b,r,3000) for k in occ.keys('M10',query) for o,r in occ.occupants(k)),pin
 for n in spec['nets']:
  if n['driver'].startswith(block+'.'):assert directions[n['driver'].split('.',1)[1]]=='OUTPUT',n
  for sink in n['sinks']:
   if sink.startswith(block+'.'):assert directions[sink.split('.',1)[1]]=='INPUT',n
 assert count==total
 assert proof[key]['native_selected_drc_violations']==0 and proof[key]['native_complete_netlist_preserved']
 assert (folder/'native.drc').stat().st_size==0
 assert (folder/'merge-receipt.txt').read_text().startswith('PASS:')
 assert len((folder/'selected-nets.txt').read_text().splitlines())==proof[key]['native_selected_nets_routed']
receipt=load(case/'stream-receipt.json')
assert receipt['compute_block_count']==9 and receipt['shape_round_trip'] and receipt['all_v10_cuts_enclosed_by_native_or_lower_adapter_m10']
assert receipt['sha256']==sha(case/'271-nine-native-four-links.oas')
assert receipt['verified_contact_count']==2102
print(json.dumps({'passed':True,'blocks':9,'nets':1049,'branches':1053,'groups':dict(Counter(r['group'] for r in rows)),
 'native_C_contacts':512,'native_P2_contacts':412,'bounds_mm':[v/2e6 for v in place['bounds_dbu'][2:]],
 'area_mm2':place['bounds_dbu'][2]*place['bounds_dbu'][3]/4e12},indent=2))
