import pya,json,hashlib,collections,os
from pathlib import Path
p=Path('.')
def rows(name): return [x.split('\t') for x in (p/name).read_text().splitlines()]
def regions(name):
 d=collections.defaultdict(pya.Region)
 for a in rows(name):
  rail,_,layer=a[:3]; d[rail,layer].insert(pya.Box(*[int(x)*5 for x in a[3:7]]))
 return {k:v.merged() for k,v in d.items()}
orig=regions('original-sboxes.tsv'); norm=regions('normalized-sboxes.tsv'); cur=regions('candidate-sboxes.tsv')
delta=[]
for k in sorted(set(norm)|set(cur)):
 x=norm.get(k,pya.Region())^cur.get(k,pya.Region())
 if not x.is_empty(): delta.append({'rail':k[0],'layer':k[1],'xor_um2':x.area()*1e-8})
assert not delta,delta
assert sorted(rows('normalized-bpins.tsv'))==sorted(rows('candidate-bpins.tsv'))
pg=rows('pg-check.tsv');assert sorted(pg)==[['VDD','0','1'],['VSS','0','1']],pg
old={tuple(a) for a in rows('original-bpins.tsv')};new={tuple(a) for a in rows('candidate-bpins.tsv')};added=sorted(new-old);removed=sorted(old-new)
lay=pya.Layout();lay.read(os.environ['PG_GDS']);top=lay.top_cell();dbu=2000
assert abs(lay.dbu-.0001)<1e-12; scale=1
layers={'metal1':11,'metal2':13,'metal3':15,'metal4':17,'metal5':19,'metal6':21,'metal7':23,'metal8':25,'metal9':27,'metal10':29}
gds={}
checks=[]
for a in sorted(new):
 pin,net,layer=a[:3]; assert pin==net and net in ('VDD','VSS'),a
 rect=pya.Region(pya.Box(*[int(x)*5 for x in a[3:7]]));same=cur.get((net,layer),pya.Region());other=cur.get(('VSS' if net=='VDD' else 'VDD',layer),pya.Region())
 assert (rect-same).is_empty(),('pin_not_same_named_PG_material',a)
 assert (rect&other).is_empty(),('pin_overlaps_opposite_PG',a)
 if layer not in gds:gds[layer]=pya.Region(top.begin_shapes_rec(lay.find_layer(layers[layer],0))).transformed(pya.ICplxTrans(scale,0,False,0,0)).merged()
 assert (rect-gds[layer]).is_empty(),('pin_not_actual_GDS_material',a)
 checks.append({'pin':pin,'net':net,'layer':layer,'box_dbu':list(map(int,a[3:7])),'added':tuple(a) in set(added),'same_named_sbox_covers':True,'opposite_rail_disjoint':True,'actual_gds_covers':True})
physical=[]
for k in sorted(set(orig)|set(cur)):
 a=orig.get(k,pya.Region());b=cur.get(k,pya.Region()); physical.append({'rail':k[0],'layer':k[1],'added_um2':(b-a).area()*1e-8,'removed_um2':(a-b).area()*1e-8})
def sha(q):return hashlib.sha256(Path(q).read_bytes()).hexdigest()
json.dump({'passed':True,'accepted':False,'root_disposition_required':True,'normalized_to_candidate_PG_specialwire_material_exact':True,'normalized_to_candidate_PG_BPins_exact':True,'original_to_candidate_BPins_added':len(added),'original_to_candidate_BPins_removed':len(removed),'added':added,'removed':removed,'all_final_pin_checks':checks,'original_to_candidate_PG_material_by_rail_layer':physical,'uncached_PG':pg,'hashes':{str(q):sha(q) for q in list(p.glob('*.tsv'))+[Path(os.environ['PG_GDS'])]},'scope':'PG boundary material and same-net ODB ownership; no parent STA/full-deck acceptance. Signal/die/macro invariance is the separate 120217 receipt.'},open('receipt.json','w'),indent=2)
