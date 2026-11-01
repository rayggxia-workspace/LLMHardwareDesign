"""Read actual remaining composed-R routes in parallel with full neighborhoods."""
from collections import Counter
from decimal import Decimal
import json,re

def inspect(root,out,cpus,run):
    from io_slots import file_sha
    from native_escape import records
    from revision300_v_transition import decode
    from revision300_v_via_batch import name_of,token_hash
    assert cpus==16
    base=out.parents[2];source=base/'block-v1-20261101-880/tasks/revision300-r-composed-vias'
    receipt=json.loads((source/'receipt.json').read_text());assert receipt['passed']and receipt['mode']==source.name
    names=('revision300-r-composed-vias.json','composed-candidate.odb','composed-candidate.def','composed-native-drc.rpt')
    for n in names:assert file_sha(source/n)==receipt['outputs'][n]
    prior=json.loads((source/names[0]).read_text());assert prior['passed']and prior['combined']and prior['candidate_native_count']==55 and prior['added_markers']==0
    assert prior['original_inputs_unchanged']and prior['exact_normal_net_header_path_rect_and_nonnet_delta']
    assert prior['ancestral_source_receipt_sha256']=='759cae257ff6731b8424eac6270a7bf255b6f0dc980ba0ff3a7bb508037b916b'
    text=(source/'composed-native-drc.rpt').read_text()
    pattern=r'violation type: (Metal Spacing|NS Metal)\n\s*srcs: net:([^\n]+)\n\s*bbox = \(([-\d.]+), ([-\d.]+)\) - \(([-\d.]+), ([-\d.]+)\) on Layer (metal\d+)'
    markers=[]
    for m in re.finditer(pattern,text):
        kind,name,*coords,layer=m.groups();box=[Decimal(v)*2000 for v in coords]
        assert all(v==int(v)for v in box)and 'net:'not in name and not re.search(r'\s',name)
        markers.append(dict(type=kind,net=name.replace('\\',''),layer=layer,bbox_dbu=list(map(int,box))))
    assert len(markers)==text.count('violation type:')==55
    assert Counter(m['layer']for m in markers)==dict(metal1=2,metal2=23,metal3=30)
    wanted={m['net']for m in markers};nets={};count=0
    for record in records(source/'composed-candidate.def'):
        count+=1;name=name_of(record)
        if name not in wanted:continue
        assert name not in nets;header,paths,rects=decode(record)
        nets[name]=dict(header=header,nonrect_paths=paths,rectangles=list(rects.elements()),original_record_token_sha256=token_hash(record))
    assert set(nets)==wanted and count==1013372
    (out/'observed-routes.json').write_text(json.dumps(nets,indent=2)+'\n')
    unchanged=all(file_sha(source/n)==receipt['outputs'][n]for n in names)
    result=dict(passed=unchanged,physical_qualified=False,diagnostic_only=True,source_task=str(source),source_receipt_sha256=file_sha(source/'receipt.json'),source_files_sha256={n:receipt['outputs'][n]for n in names},source_native_count=55,markers=markers,normal_net_count=count,observed_net_count=len(nets),original_inputs_unchanged=unchanged,scope='Readonly actual88055-marker DEF routes/RECTs, including all prior via rewrites and314 corner fills. Runs independently of complete composed-neighborhood export; future pruning must join that actual fresh geometry. One16CPU real prerequisite, not repeated filler. No edit or repair/final qualification.')
    (out/'revision300-r-composed-topology.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed']
