"""Receive only successful exact-source final gates, then package real native views."""
from pathlib import Path
import argparse,hashlib,json,subprocess,os,shutil,tarfile,csv
p=argparse.ArgumentParser()
for n in ['physical','evaluation','functional','geometry','mapped','mapping-proof']:p.add_argument('--'+n,type=Path,required=True)
p.add_argument('--capacity',type=int,choices=[256,1024],required=True);a=p.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
P=Path(__file__).resolve().parent;R=a.physical/'flow/results/nangate45'/('r166_'+str(a.capacity))/'base'
O=Path.cwd()/'delivery';O.mkdir(exist_ok=False);checks={};evidence={}
def receive(path):
 obj=read(path);evidence[str(path)]=sha(path);return obj
e=receive(a.evaluation/'receipt.json');f=receive(a.functional/'receipt.json');g=receive(a.geometry/'GEOMETRY.json')[0];m=receive(a.mapped/'receipt.json')
checks['complete_physical']=e['passed']is True and e['capacity']==a.capacity and e['physical']==str(a.physical)and bool(e['checks'])and all(e['checks'].values())
checks['exact_final_function']=f['passed']is True and f['capacity']==a.capacity and f['inputs'][str(R/'6_final.v')]==sha(R/'6_final.v')
checks['complete_3_by_63_and_protocol']=len(f['tasks'])==192 and all(r['passed']is True for r in f['tasks']) and all({r['case']for r in f['tasks']if r['initialization']==i}==set(range(-1,63))for i in range(3))
checks['exact_geometry']=g['def_sha256']==sha(R/'6_final.def')and g['spef_sha256']==sha(R/'6_final.spef')and g['all_selection_tree_nets_extracted']and g['centerline_matches_router_within_2um_each_layer']and all(s['exit']==0 for s in g['stages'])
proof=receive(a.mapping_proof/'receipt.json')
checks['complete_mapping_formal']=proof['passed']is True and proof['proof']['passed']is True and proof['mapped']==str(a.mapped)and proof['inputs'][str(a.mapped/'mapped.json')]==sha(a.mapped/'mapped.json')and proof['source_sha256']==m['source_sha256']
for path,digest in proof['inputs'].items():assert sha(Path(path))==digest
checks['mapped_structure']=m['passed']is True and m['mapped_json_sha256']==sha(a.mapped/'mapped.json')
for path,row in e['artifacts'].items():assert sha(Path(path))==row['sha256']
for path,digest in f['inputs'].items():assert sha(Path(path))==digest
lineage=[];q=a.physical;seen=set()
while True:
 assert q not in seen;seen.add(q);v=receive(q/'receipt.json');assert v.get('exit')==0 or q!=a.physical
 lineage.append({'physical':str(q),'receipt_sha256':sha(q/'receipt.json')})
 for path,digest in v.get('source_hashes',{}).items():assert sha(Path(path))==digest
 sources=[v[k]for k in ['source_cts','source_placed','source_gpl']if k in v]
 if not sources:
  checks['mapped_lineage']=v['mapped_json_sha256']==m['mapped_json_sha256']and v['source_sha256']==m['source_sha256'];break
 assert len(sources)==1;q=Path(sources[0])
checks['original_acceptance_sdc']=sha(a.physical/'input.sdc')==sha(P/'physical.sdc')
checks['source_files_present']=bool(m['source_sha256'])
for path,digest in m['source_sha256'].items():
 actual=P.parent.parent/'rtl/r_local_state'/Path(path).name
 assert actual.is_file()and sha(actual)==digest,'Packaged RTL differs from proved mapped source'
result={'passed':all(checks.values()),'capacity':a.capacity,'checks':checks,'evidence':evidence,'lineage':lineage,'frequency_mhz':300,'state_bytes':a.capacity*8,'state_versions':2,'lanes':8,'read_storage_edges':'E0 request,E1 select,E2 local data,E3 merge,E4 external enqueue','native_leaf_qualified':all(checks.values()),'hierarchical_lib_timing_qualified':False,'m11_m12_system_qualified':False,'scope':'Exact standalone local-state R macro. Native final physical acceptance only; no system or old ISA substitution claim.'}
(O/'QUALIFICATION.json').write_text(json.dumps(result,indent=2)+'\n');assert result['passed'],checks
for sub in ['native','abstract','evidence','source','meta']:(O/sub).mkdir()
with(O/'meta/CASE_CYCLES.csv').open('w',newline='')as stream:
 writer=csv.writer(stream);writer.writerow(['initialization','case','mode','elements','layers','tokens','checks','cycles','logical_time_us_at_300MHz'])
 for row in sorted(f['tasks'],key=lambda r:(r['initialization'],r['case'])):
  if row['case']<0:continue
  case=row['corpus'];score=row['result'];cycles=score['cycles']
  writer.writerow([row['initialization'],row['case'],case['mode'],case['elements'],case['layers'],case['tokens'],score['checks'],cycles,cycles/300.0])
summary=f'''# R local-state {a.capacity}: exact standalone native macro

Two state versions, {a.capacity*8} state bytes total, eight arithmetic lanes.
Ordinary standard-cell storage; not a foundry SRAM macro.
Original 300MHz / I/O SDC, fixed internal M1–M10, 821 internal M10 signal pins.

Final extracted setup: {e['metrics']['finish__timing__setup__ws']} ns.
Final extracted hold: {e['metrics']['finish__timing__hold__ws']} ns.
All required physical checks passed; complete original GDS items: {e['full_deck_items']}.
Exact final cell netlist: 189 numeric cases and three protocol tests passed.
Actual final-cell cycle counts are in meta/CASE_CYCLES.csv; time is cycles/300MHz,
not a full-model, power or system performance measurement.

Native files are in native/; actual-source abstract views are in abstract/.
Evidence, source and lineage are preserved with per-member MANIFEST hashes.
No old-ISA substitution, hierarchical timing-model or M11/M12 system qualification.
'''
(O/'MEASURED_SUMMARY.md').write_text(summary)
files={}
for suffix in ['v','sdc','def','odb','spef','gds']:
 src=R/('6_final.'+suffix);assert src.is_file()and src.stat().st_size>0;dest=O/'native'/src.name;shutil.copyfile(src,dest);files[src.name]={'sha256':sha(dest),'bytes':dest.stat().st_size}
for name in ['r_stream_local.lef','r_stream_local_typ.lib']:shutil.copyfile(R/name,O/'abstract'/name)
# Render the actual accepted GDS, preserving every layer; a picture is not DRC evidence.
script="import pya\nv=pya.LayoutView()\nv.load_layout("+repr(str(O/'native/6_final.gds'))+",0)\nv.max_hier()\nv.add_missing_layers()\nv.zoom_fit()\nv.save_image("+repr(str(O/'native/layout.png'))+",1600,1600)\n"
(O/'meta/render.py').write_text(script)
with(O/'meta/render.log').open('w')as log:subprocess.run(['env','QT_QPA_PLATFORM=offscreen','klayout','-z','-r',str(O/'meta/render.py')],stdout=log,stderr=subprocess.STDOUT,check=True)
assert(O/'native/layout.png').stat().st_size>1000
shutil.copytree(a.evaluation,O/'evidence/physical')
shutil.copytree(a.functional,O/'evidence/final-function')
shutil.copytree(a.geometry,O/'evidence/geometry')
shutil.copytree(a.mapping_proof,O/'evidence/mapping-formal')
shutil.copyfile(a.mapped/'receipt.json',O/'evidence/mapped-receipt.json')
shutil.copyfile(a.mapped/'SELECTION.json',O/'evidence/mapped-selection.json')
shutil.copytree(P.parent.parent/'rtl/r_local_state',O/'source/rtl')
shutil.copytree(P,O/'source/runners')
for i,row in enumerate(lineage):
 src=Path(row['physical']);d=O/'meta'/('lineage%02d'%i);d.mkdir()
 for name in ['receipt.json','config.mk','input.sdc','regions.json','HOLD_ENDPOINT_ECO.tsv','INPUT_HOLD_AUDIT.tsv','PORT_BUFFER_AUDIT.tsv','EXTRACTED_PATH_BINDING.json','EXTRACTED_INPUT_ECO.tsv','CLOCK_ROOT_AUDIT.tsv']:
  if(src/name).exists():shutil.copyfile(src/name,d/name)
 for name in ['FILES.sha256','run.sbatch','source-check.log']:
  if(src.parent/name).exists():shutil.copyfile(src.parent/name,d/name)
# Preserve the actual frozen runner/RTL source, not merely today's package code.
base=a.physical.parent.parent
attempts={Path(row['physical']).parent for row in lineage}|{a.evaluation.parent,a.functional.parent,a.geometry.parent,a.mapping_proof.parent,a.mapped.parents[1],Path.cwd()}
if e.get('source_receiver'):attempts.add(Path(e['source_receiver']).parent)
if e.get('complete_native'):attempts.add(Path(e['complete_native']['source']).parent)
binding=read(a.functional/'BUILD_BINDING.json');attempts.add(Path(binding['source_test']).parent)
archives={}
for archive in sorted(base.glob('source*.tar')):
 with tarfile.open(archive)as t:
  members={entry.name:hashlib.sha256(t.extractfile(entry).read()).hexdigest()for entry in t.getmembers()if entry.isfile()}
  archives[archive.name]={'file_sha256':members,'git_archive_commit':t.pax_headers.get('comment'),'archive_sha256':sha(archive)}
(O/'source/archives').mkdir();source_index=[]
for attempt in sorted(attempts):
 assert attempt.parent==base,'Foreign task source directory rejected'
 index=attempt/'FILES.sha256';assert index.is_file()
 actual={line.split(None,1)[1].lstrip('*'):line.split(None,1)[0]for line in index.read_text().splitlines()if line.strip()}
 matches=[name for name,row in archives.items()if row['file_sha256']==actual];assert matches,(str(attempt),'No exact frozen source archive')
 for name,expected in actual.items():assert sha(attempt/name)==expected
 chosen=matches[0];dest=O/'source/archives'/chosen
 if not dest.exists():shutil.copyfile(base/chosen,dest)
 source_index.append({'attempt':str(attempt),'files_sha256':sha(index),'matching_archive':chosen,'archive_sha256':sha(dest),'matching_git_commit':archives[chosen]['git_archive_commit'],'all_exact_content_archive_matches':matches})
(O/'meta/FROZEN_SOURCE_INDEX.json').write_text(json.dumps(source_index,indent=2)+'\n')
(O/'meta/SIX_FILES.json').write_text(json.dumps(files,indent=2)+'\n')
manifest={str(f.relative_to(O)):{'sha256':sha(f),'bytes':f.stat().st_size}for f in O.rglob('*')if f.is_file()}
(O/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
archive=O.parent/('R-local-state-%d-300MHz.tar.gz'%a.capacity)
with tarfile.open(archive,'w:gz')as t:t.add(O,arcname='R-local-state-'+str(a.capacity))
(O.parent/'DELIVERY_RECEIPT.json').write_text(json.dumps({'passed':True,'archive':str(archive),'sha256':sha(archive),'bytes':archive.stat().st_size,'members':len(manifest)+1,'six_files':files,'scope':'Server bundle only; local download/hash/member reception remains separate'},indent=2)+'\n')
