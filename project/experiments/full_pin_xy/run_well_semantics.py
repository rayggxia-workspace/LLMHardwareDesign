"""Validate the installed WELL.4 expression against isolated geometric facts."""
from pathlib import Path
from collections import Counter
import datetime,json,os,subprocess,xml.etree.ElementTree as ET
from run_exports import ROOT,IMAGE,sha

driver=Path(__file__).resolve().parent;out=ROOT/'rule_semantics/well4-r01';out.mkdir(parents=True,exist_ok=False)
common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
with (out/'fixtures.log').open('x') as f:r=subprocess.run(common+[IMAGE,'/usr/bin/klayout','-b','-r',str(driver/'make_well_fixtures.py'),'-rd','outdir='+str(out)],stdout=f,stderr=subprocess.STDOUT)
assert r.returncode==0,'Native fixture creation failed'
fixtures=json.loads((out/'fixtures.json').read_text());rows=[]
for name,boxes in fixtures['fixtures'].items():
    report=out/(name+'.lyrdb')
    with (out/(name+'.log')).open('x') as f:r=subprocess.run(common+[IMAGE,'/usr/bin/klayout','-b','-r',str(driver/'well4_semantics.drc'),'-rd','input='+str(out/(name+'.gds')),'-rd','report='+str(report)],stdout=f,stderr=subprocess.STDOUT)
    assert r.returncode==0 and report.exists(),name
    tree=ET.parse(str(report));counts=Counter(e.findtext('category').strip("'") for e in tree.findall('.//item'))
    rows.append({'fixture':name,'rectangles_nm':boxes,'counts':dict(counts),'GDS_sha256':sha(out/(name+'.gds')),'native_report_sha256':sha(report)})
byname={r['fixture']:r['counts'] for r in rows}
assert byname['wide_isolated'].get('WIDTH200_REFERENCE',0)==0
assert byname['thin_isolated'].get('WIDTH200_REFERENCE',0)>0
assert byname['wide_gap150'].get('WIDTH200_REFERENCE',0)==byname['wide_gap150'].get('SPACE135_REFERENCE',0)==0
assert byname['wide_gap100'].get('SPACE135_REFERENCE',0)>0
mismatch=any(bool(r['counts'].get('ORIGINAL_WELL4',0))!=bool(r['counts'].get('WIDTH200_REFERENCE',0)) for r in rows)
deck='/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc'
deck_sha=subprocess.check_output(common+[IMAGE,'sha256sum',deck]).decode().split()[0]
summary={'scope':'RULE_IMPLEMENTATION_SEMANTICS_ONLY; synthetic rectangles, not circuit qualification','scheduler_job':os.environ['SLURM_JOB_ID'],
 'driver_commit':(driver/'driver_commit.txt').read_text().strip(),'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'installed_original_deck':deck,'installed_original_deck_sha256':deck_sha,'original_deck_unmodified':True,
 'original_WELL4_expression':'well.separation(well, 200.nm, euclidian)','original_WELL4_description':'Minimum width of nwell/pwell : 200nm',
 'official_method_reference':'https://www.klayout.de/doc/about/drc_ref_layer.html','probe_runset_sha256':sha(driver/'well4_semantics.drc'),
 'fixtures':rows,'original_expression_differs_from_width_reference_on_fixtures':mismatch,
 'conclusion':'SEMANTIC_MISMATCH_CONFIRMED; original raw counts retained, do not label all WELL.4 markers true width violations' if mismatch else 'NO_DIFFERENCE_IN_THIS_FIXTURE_SET; no design pass inferred',
 'qualified_design_or_rule_deck':False,'full_original_design_reports_changed':False}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print('WELL4_SEMANTIC_PROBE',summary['conclusion'],rows)
