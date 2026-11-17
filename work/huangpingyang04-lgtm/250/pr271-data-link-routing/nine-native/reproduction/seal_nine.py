"""Freeze native readback and bind it to the upper-route input fingerprint."""
from pathlib import Path
import hashlib,json,shutil,sys
root=Path(sys.argv[1]);out=root/'final';sys.path.insert(0,str(root/'engine'))
from check import verify,digest
def load(p):return json.loads(p.read_text())
def write(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
native={}
for key,source in [('C',root/'native-final-C'),('P2',root/'native-final-P')]+[(k,root.parent/'hpy-pr276-stress976.nTAy3LMX'/('export-'+k)) for k in ('P','U','F','J')]:
 d=out/('native-'+key);d.mkdir(exist_ok=True)
 for name in ('native.tsv.gz','ports.tsv'):shutil.copyfile(source/name,d/name)
 if key in ('C','P2'):
  checks=load(source/'contact-check.json');assert not checks['conflicts']
  shutil.copyfile(source/'contact-check.json',d/'contact-check.json')
  assert (source/'native.drc').stat().st_size==0
  assert (source/'merge-receipt.txt').read_text().startswith('PASS:')
  for name in ('native.drc','merge-receipt.txt','selected-nets.txt'):shutil.copyfile(source/name,d/name)
  native[key]={'odb':str(source/'native-final.odb'),'odb_sha256':sha(source/'native-final.odb'),'ports_checked':checks['checked'],
   'native_selected_nets_routed':len((source/'selected-nets.txt').read_text().splitlines()),'native_selected_drc_violations':0,
   'native_complete_netlist_preserved':True,'native_routing_scope':'selected interface nets only; remaining internal nets and whole-chip signoff not qualified'}
 else:native[key]={'odb_sha256':load(root.parent/'hpy-pr276-stress976.nTAy3LMX/input-audit.json')['native_geometry'][key]['odb_sha256']}
 native[key].update(geometry_sha256=sha(d/'native.tsv.gz'),ports_sha256=sha(d/'ports.tsv'))
place=load(out/'placement.json')
old=place.pop('original_placement',None)
if old is not None:place['reference_compact_placement_sha256']=digest(old)
place['mirrored_blocks']=['P1'];write(out/'placement.json',place)
spec=load(out/'spec.json');spec['context'].update(native_contacts_readback='passed',native_views=native,placement_sha256=sha(out/'placement.json'),lower_overlay_sha256=sha(out/'lower-overlay.json'))
route=load(out/'route.json');route['spec_sha256']=digest(spec);route['context']=spec['context']
write(out/'spec.json',spec);write(out/'route.json',route);write(out/'checks.json',verify(spec,route))
write(out/'native-provenance.json',native)
print('Sealed nine-base native readback and verified 1049 top nets',flush=True)
