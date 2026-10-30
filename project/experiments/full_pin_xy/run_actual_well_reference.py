"""Additional actual-layout width/space diagnostics; original full deck retained.

Never replace the original deck, delete markers, or claim a complete DRC pass.
Requires a strict-complete baseline GDS and a proven semantic fixture mismatch.
"""
from pathlib import Path
from collections import Counter
import datetime,json,os,re,subprocess,sys,xml.etree.ElementTree as ET
from run_exports import ROOT,IMAGE,sha

driver=Path(__file__).resolve().parent;prior=json.loads((ROOT/'rule_semantics/well4-r01/summary.json').read_text())
assert prior['original_expression_differs_from_width_reference_on_fixtures']
source=ROOT/'streamout/r03/llaccel_aux-A';original=json.loads((source/'execution.json').read_text());gds=source/'diagnostic.gds'
assert original['merge_returncode']==0 and not original['missing_GDS_cells']
assert sha(gds)==original['files']['diagnostic.gds']['sha256']
revision=sys.argv[1] if len(sys.argv)>1 else 'r01';assert revision.replace('-','').isalnum()
out=ROOT/'rule_semantics'/('llaccel-A-well-reference-'+revision);out.mkdir(parents=True,exist_ok=False)
common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
deck='/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc'
raw=subprocess.check_output(common+[IMAGE,'cat',deck]);code=ET.fromstring(raw).findtext('text');assert code
deck_sha=__import__('hashlib').sha256(raw).hexdigest()
assert deck_sha==prior['installed_original_deck_sha256']==json.loads((source/'merge.json').read_text())['inputs_sha256'][deck]
context=[s.strip() for s in code.splitlines() if re.fullmatch(r'\s*(?:(?:tiles|tile_borders)\([\d.]+\.um\)|deep)\s*',s)]
assert 'deep' in context and any(s.startswith('tiles(') for s in context) and any(s.startswith('tile_borders(') for s in context)
definitions=[]
for name in ['nwell','pwell']:
    m=re.search(r'^\s*'+name+r'\s*=\s*(?:input|polygons)\([^\n]+\)\s*$',code,re.M);assert m,(name,'native input mapping not resolved')
    definitions.append(m[0].strip())
runset=(driver/'well4_semantics.drc').read_text();runset=runset.replace('well = input(21, 0).or(input(22, 0))','\n'.join(context+definitions)+'\nwell = nwell.or(pwell)')
script=out/'actual_reference.drc';script.write_text(runset)
runset+='\nnwell.width(200.nm, euclidian).output("NWELL_WIDTH200_REFERENCE", "Additional individual nwell width check")\npwell.width(200.nm, euclidian).output("PWELL_WIDTH200_REFERENCE", "Additional individual pwell width check")\n'
runset+='nwell.space(135.nm, euclidian).output("NWELL_SPACE135_REFERENCE", "Additional individual nwell spacing check")\npwell.space(135.nm, euclidian).output("PWELL_SPACE135_REFERENCE", "Additional individual pwell spacing check")\n'
script.write_text(runset)
report=out/'actual_reference.lyrdb'
with (out/'reference.log').open('x') as f:r=subprocess.run(common+[IMAGE,'klayout','-b','-r',str(script),'-rd','input='+str(gds),'-rd','report='+str(report)],stdout=f,stderr=subprocess.STDOUT)
assert r.returncode==0 and report.exists()
counts=Counter()
declared=[e.findtext('name') for e in ET.parse(str(report)).findall('./categories/category')]
for name in declared:counts[name]=0
for event,e in ET.iterparse(str(report),events=['end']):
    if e.tag=='item':counts[e.findtext('category').strip("'")]+=1;e.clear()
old=Counter()
for event,e in ET.iterparse(str(source/'diagnostic.lyrdb'),events=['end']):
    if e.tag=='item':old[e.findtext('category').strip("'")]+=1;e.clear()
summary={'scope':'ADDITIONAL_ACTUAL_LAYOUT_RULE_SEMANTICS_DIAGNOSTIC_ONLY; not a replacement full deck or signoff',
 'case':'llaccel_aux','plan':'A','scheduler_job':os.environ['SLURM_JOB_ID'],'driver_commit':(driver/'driver_commit.txt').read_text().strip(),
 'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'strict_complete_GDS_sha256':sha(gds),'source_streamout_receipt_sha256':sha(source/'execution.json'),
 'original_full_report_sha256':sha(source/'diagnostic.lyrdb'),'original_full_report_counts':dict(old),'actual_reference_counts':dict(counts),
 'original_WELL4_count_reproduced':old.get('WELL.4',0)==counts.get('ORIGINAL_WELL4',0),
 'original_deck_unmodified':True,'installed_original_deck_sha256':deck_sha,'original_hierarchy_and_tiling_context_preserved':context,'allocated_checker_threads':1,
 'actual_well_layer_mapping_from_original_source':definitions,'source_notes_WELL2_not_coded':'was not coded' in code and 'WELL.2' in code,
 'declared_reference_checks':declared,'reference_mask_scope':'WIDTH200_REFERENCE/SPACE135_REFERENCE operate on the nwell|pwell union; individual NWELL/PWELL checks are separately named. Different-potential WELL.2 remains unimplemented/unverified.',
 'reference_runset_sha256':sha(script),'reference_report_sha256':sha(report),'original_full_reports_reclassified_as_pass':False,
 'full_qualification':False,'remaining_conditions':'Original antenna reports, missing/unverified applicable rules including WELL.2, LVS, system timing and SRAM views still separate; no rule waivers.'}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print('ACTUAL_WELL_REFERENCE',counts,'original',old.get('WELL.4'),flush=True)
