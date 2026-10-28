"""Run in KLayout: correlate actual antenna polygons with actual routed conductors.

No bbox-only net assignment. Ambiguous and unmatched polygons stay unresolved.
This correlation is not a substitute for LVS or a repaired DRC result.
"""
from pathlib import Path
from collections import defaultdict,Counter
import csv,gzip,hashlib,json,math,os,re,xml.etree.ElementTree as ET
import pya

out=Path(os.environ['PINXY_ANTENNA_MAP_OUT']);spec=json.loads((out/'input.json').read_text())
DBU=.0005;TILE=128000
markers=[];regions=[];index=defaultdict(set)
for event,item in ET.iterparse(spec['RDB'],events=['end']):
    if item.tag!='item':continue
    category=item.findtext('category','').strip("'");match=re.fullmatch(r'METAL(\d+)_ANTENNA',category)
    assert match,('Unexpected finding retained; need separate handling',category)
    values=[v.text or '' for v in item.findall('values/value')];polytexts=[s[len('polygon: '):] for s in values if s.startswith('polygon: ')]
    assert polytexts and item.findtext('cell')==spec['top'],'Unsupported hierarchical marker, not silently transformed'
    region=pya.Region()
    for text in polytexts:region.insert(pya.DPolygon.from_s(text).to_itype(DBU))
    region.merge();box=region.bbox();n=len(markers);layer='metal'+match[1]
    props={}
    for value in values:
        m=re.match(r'\[#([^]]+)\] float: (.*)',value)
        if m:props[m[1]]=float(m[2])
    markers.append({'marker_id':n,'category':category,'layer':layer,'cell':item.findtext('cell'),
      'actual_GDS_metal_polygon_texts_um':polytexts,'reported_measurements':props,
      'source_polygon_bbox_um':[box.left*DBU,box.bottom*DBU,box.right*DBU,box.top*DBU],
      'net_mapping':'NOT_YET_CORRELATED','candidate_net_intersection_area_sum_um2':{}})
    regions.append(region)
    for i in range(box.left//TILE,box.right//TILE+1):
        for j in range(box.bottom//TILE,box.top//TILE+1):index[layer,i,j].add(n)
    item.clear()
assert isinstance(spec['expected_findings'],int) and spec['expected_findings']>0
assert len(markers)==spec['expected_findings']
reuse=spec.get('reuse_correlations_from')
if reuse:
    previous=json.loads((Path(reuse)/'marker_net_correlations.json').read_text())
    assert len(previous)==len(markers)
    for old,new in zip(previous,markers):
        for key in ['marker_id','category','layer','cell','actual_GDS_metal_polygon_texts_um','reported_measurements','source_polygon_bbox_um']:
            assert old[key]==new[key],('RDB correlation source changed',key)
        assert old['net_mapping'] in ['UNIQUE_EXACT_POLYGON_CONDUCTOR_CORRELATION','AMBIGUOUS_MULTIPLE_NETS','NO_NATIVE_CONDUCTOR_MATCH']
    markers=previous;native_rows=None;exact_tests=None
else:
    scores=[Counter() for m in markers];native_rows=0;exact_tests=0;metal_layers={'metal'+str(i) for i in range(2,11)}
    with gzip.open(spec['native_conductors'],'rt') as f:
        for q in csv.DictReader(f,delimiter='\t'):
            native_rows+=1;layer=q['layer']
            if layer not in metal_layers:continue
            a,b,c,d=[int(q[k]) for k in ['x0','y0','x1','y1']];candidates=set()
            for i in range(a//TILE,c//TILE+1):
                for j in range(b//TILE,d//TILE+1):candidates.update(index.get((layer,i,j),()))
            if not candidates:continue
            box=pya.Box(a,b,c,d);shape=pya.Region(box)
            for n in candidates:
                if not regions[n].bbox().overlaps(box):continue
                exact_tests+=1;area=(regions[n]&shape).area()
                if area>0:scores[n][q['net']]+=area*DBU*DBU
            if native_rows%500000==0:print('CORRELATION_PROGRESS',native_rows,exact_tests,flush=True)
    for m,score in zip(markers,scores):
        m['candidate_net_intersection_area_sum_um2']=dict(score)
        m['area_note']='Sum over native rectangles may double count wire/via overlap; used only to identify distinct positive-area net correlations, not metal/gate area or RC.'
        m['net_mapping']='UNIQUE_EXACT_POLYGON_CONDUCTOR_CORRELATION' if len(score)==1 else 'AMBIGUOUS_MULTIPLE_NETS' if score else 'NO_NATIVE_CONDUCTOR_MATCH'
        m['native_net']=next(iter(score)) if len(score)==1 else None
(out/'marker_net_correlations.json').write_text(json.dumps(markers,indent=2)+'\n')
unique=sorted({m['native_net'] for m in markers if m['native_net']})
(out/'unique_correlated_native_nets.json').write_text(json.dumps(unique,indent=2)+'\n')
layout=pya.Layout();layout.read(spec['standard_GDS']);cell=layout.cell('ANTENNA_X1')
inventory={'actual_standard_GDS_cell_found':cell is not None,'actual_standard_GDS_cell_nonempty':cell is not None and not cell.is_empty()}
if cell is not None:
    bb=cell.bbox();inventory['actual_GDS_bbox_um']=[bb.left*layout.dbu,bb.bottom*layout.dbu,bb.right*layout.dbu,bb.top*layout.dbu]
    code=ET.parse(spec['deck']).getroot().findtext('text');layers={}
    for name,l,dt in re.findall(r'(\w+)\s*=\s*(?:input|polygons)\(\s*(\d+)\s*(?:,\s*(\d+)\s*)?\)',code):layers[name]=(int(l),int(dt or 0))
    assert all(n in layers for n in ['nplus','active','nwell','cont']),layers
    def mask(name):return pya.Region(cell.begin_shapes_rec(layout.layer(*layers[name])))
    diode=(mask('nplus')&mask('active'))-mask('nwell');diode.merge()
    inventory['unchanged_deck_diode_expression']='(nplus & active) - nwell'
    inventory['diode_recognition_area_um2']=diode.area()*layout.dbu**2
    inventory['diode_contact_overlap_area_um2']=(diode&mask('cont')).area()*layout.dbu**2
summary={'scope':'READ_ONLY_EXACT_GDS_POLYGON_TO_NATIVE_CONDUCTOR_CORRELATION_AND_REAL_DIODE_INVENTORY',
  'marker_count':len(markers),'mapping_status_counts':dict(Counter(m['net_mapping'] for m in markers)),
  'unique_correlated_net_count':len(unique),'native_rows_streamed':native_rows,'exact_polygon_intersection_tests':exact_tests,
  'native_geometry_DBU_um':DBU,'reused_geometry_correlations_from':reuse,'bbox_only_assignment_used':False,'diode_inventory':inventory,
  'original1460_findings_repaired':False,'functional_or_LVS_proof':False,'full_qualification':False,
  'klayout_version':pya.__version__,'not_claimed':['Full rules passed','Actual antenna repair completed','Uniform gate area model invented','Ambiguous findings assigned a guessed net'],
  'source_files_SHA256':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in [spec['RDB'],spec['native_conductors'],spec['standard_GDS'],spec['deck']]}}
if spec.get('existing_real_diode_nets'):
    path=Path(spec['existing_real_diode_nets']);existing=set(json.loads(path.read_text()))
    assert len(existing)==636
    summary['existing_real_diode_netlist_SHA256']=hashlib.sha256(path.read_bytes()).hexdigest()
    summary['mapped_nets_already_with_real_diode']=sorted(set(unique)&existing)
    summary['mapped_nets_without_existing_real_diode']=sorted(set(unique)-existing)
    summary['protected_net_membership_not_GDS_LVS_or_antenna_protection_proof']=True
(out/'correlation_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print('ANTENNA_CORRELATION',summary['mapping_status_counts'],len(unique),inventory,flush=True)
