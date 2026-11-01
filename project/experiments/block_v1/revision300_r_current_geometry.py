"""Read only the actual newly combined R source; no ancestral geometry reuse."""
from decimal import Decimal
import json,re


def inspect(root,out,cpus,run,topology=False):
    from io_slots import file_sha
    from revision300_r_neighborhood_export import export
    from native_escape import records
    from revision300_v_transition import decode
    from revision300_v_via_batch import name_of,token_hash
    assert cpus==16
    source=out.parents[2]/'block-v1-20261101-903/tasks/revision300-r-current-compose'
    receipt=json.loads((source/'receipt.json').read_text());assert receipt['passed'] and receipt['mode']==source.name
    names=('revision300-r-remaining.json','remaining-candidate.odb','remaining-candidate.def','remaining-native-drc.rpt','remaining.tcl')
    for name in names:assert file_sha(source/name)==receipt['outputs'][name]
    prior=json.loads((source/names[0]).read_text())
    assert prior['passed'] and prior['combined'] and prior['original_inputs_unchanged'] and prior['exact_normal_net_header_path_rect_and_nonnet_delta'] and prior['added_markers']==0
    assert prior['source_receipt_sha256']=='4054eef392ce7c7a966b3774d51eb39d27540d88f6f7f52196692f520eac6938'
    count=prior['candidate_native_count'];assert 0<count<55,'No geometry filler if combined source is already native-clean'
    if not topology:
        inputs={n:receipt['outputs'][n]for n in ('remaining-candidate.odb','remaining-candidate.def')}
        export(root,out,cpus,run,source,source,source/'remaining-candidate.odb',source/'remaining-candidate.def',source/'remaining-native-drc.rpt',inputs,count,dict(script_sha256=receipt['outputs']['remaining.tcl'],before_after_def_sha256=None))
        return
    text=(source/'remaining-native-drc.rpt').read_text();markers=[]
    pattern=r'violation type: (Metal Spacing|NS Metal)\n\s*srcs: net:([^\n]+)\n\s*bbox = \(([-\d.]+), ([-\d.]+)\) - \(([-\d.]+), ([-\d.]+)\) on Layer (metal\d+)'
    for match in re.finditer(pattern,text):
        kind,name,*coords,layer=match.groups();box=[Decimal(v)*2000 for v in coords]
        assert all(v==int(v)for v in box) and 'net:'not in name and not re.search(r'\s',name)
        markers.append(dict(type=kind,net=name.replace('\\',''),layer=layer,bbox_dbu=list(map(int,box))))
    assert len(markers)==text.count('violation type:')==count
    wanted={m['net']for m in markers};nets={};n=0
    for record in records(source/'remaining-candidate.def'):
        n+=1;name=name_of(record)
        if name not in wanted:continue
        assert name not in nets;header,paths,rects=decode(record)
        nets[name]=dict(header=header,nonrect_paths=paths,rectangles=list(rects.elements()),original_record_token_sha256=token_hash(record))
    assert set(nets)==wanted and n==1013372
    (out/'observed-routes.json').write_text(json.dumps(nets,indent=2)+'\n')
    unchanged=all(file_sha(source/name)==receipt['outputs'][name]for name in names)
    result=dict(passed=unchanged,physical_qualified=False,source_receipt_sha256=file_sha(source/'receipt.json'),source_native_count=count,source_files_sha256={name:receipt['outputs'][name]for name in names},markers=markers,normal_net_count=n,observed_net_count=len(nets),original_inputs_unchanged=unchanged,scope='Readonly routes/RECTs from actual newly combined903 source; joins its independent complete neighborhood before further repair. No acceptance or ancestral qualification transfer.')
    (out/'revision300-r-current-topology.json').write_text(json.dumps(result,indent=2)+'\n');assert result['passed']
