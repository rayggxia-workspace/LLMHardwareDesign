"""Locate independent GDS DRC markers in the unchanged native routed database.

Bounding-box hits are candidate geometry, not proof of GDS connectivity or a
replacement for DRC. Preserve all hits, terminals, source identities and misses.
"""
import collections
import json
import math
from pathlib import Path
import re


def windows(summary):
    result=[]
    number=r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'
    for i,item in enumerate(summary['items']):
        match=re.fullmatch(r'METAL(\d+)(?:\.\d+|_ANTENNA)',item['category'])
        assert match and 1<=int(match.group(1))<=10
        shapes=[s for s in item['values']if s.startswith(('polygon: ','edge-pair: '))]
        assert len(shapes)==1
        tokens=list(filter(None,re.split(r'[(),;|\s]+',shapes[0].split(': ',1)[1])))
        assert len(tokens)%2==0 and all(re.fullmatch(number,t)for t in tokens)
        points=[(float(tokens[k]),float(tokens[k+1]))for k in range(0,len(tokens),2)]
        assert len(points)>=4 and all(math.isfinite(v)for p in points for v in p)
        # Euclidean DRC edge-pair endpoints may lie between database units.
        # A one-DBU envelope keeps original geometry rather than rounding it.
        box=[math.floor(min(p[k]for p in points)*2000)-1 for k in (0,1)]
        box += [math.ceil(max(p[k]for p in points)*2000)+1 for k in (0,1)]
        assert box[0]<box[2]and box[1]<box[3]
        result.append(dict(index=i,category=item['category'],layer='metal'+match.group(1),
                           bbox_dbu=box,original_geometry=shapes[0]))
    return result


def verify(root,out,cpus,run):
    from io_slots import file_sha
    from native_drc import summarize
    base=out.parents[2]
    failed=base/'block-v1-20261027-094/tasks/native-cap40-receive-transaction6k-c'
    receipt=json.loads((failed/'receipt.json').read_text());assert receipt['passed']is False
    report=failed/'native-drc.lyrdb'
    assert file_sha(report)==receipt['outputs'][report.name]
    proof=failed/'native-physical-receiver.json'
    assert file_sha(proof)==receipt['outputs'][proof.name]
    physical=json.loads(proof.read_text());assert not physical['passed']
    source=base/'block-v1-20261027-093/tasks/native-cap40-run-transaction6k-c'
    assert physical['source']==str(source)
    bound=json.loads((source/'receipt.json').read_text());assert bound['passed']is True
    assert file_sha(source/'receipt.json')==physical['source_receipt_sha256']
    odb=source/'flow/results/nangate45/bv1_transaction6k_C/base/6_final.odb'
    assert file_sha(odb)==bound['outputs'][str(odb.relative_to(source))]
    assert file_sha(failed/'input-sha256.json')==receipt['outputs']['input-sha256.json']
    inputs=json.loads((failed/'input-sha256.json').read_text())
    assert inputs[str(odb)]==file_sha(odb)
    summary=summarize(report);markers=windows(summary);assert len(markers)>0
    (out/'markers.json').write_text(json.dumps(markers,indent=2)+'\n')
    script='set_thread_count %d\nread_db {%s}\nsource {%s}\n'%(cpus,odb,root/'project/experiments/block_v1/odb_geometry.tcl')
    script+='namespace eval bvgeom {variable markers [dict create]}\n'
    for marker in markers:
        script+='dict lappend bvgeom::markers %s {%d %s}\n'%(marker['layer'],marker['index'],' '.join(map(str,marker['bbox_dbu'])))
    script+='source {%s}\n'%(root/'project/experiments/block_v1/native_drc_locate.tcl')
    (out/'locate.tcl').write_text(script)
    run(['openroad','-no_init','-exit','locate.tcl'],'locate.log')
    matches=collections.defaultdict(list);netnames={};terminals=collections.defaultdict(list)
    def name(text):return bytes.fromhex(text).decode('utf-8')
    for line in(out/'marker-shapes.tsv').read_text().splitlines():
        index,net,layer,kind,*coords=line.split('\t');index=int(index)
        assert 0<=index<len(markers)and layer==markers[index]['layer']and len(coords)==4
        netnames[net]=name(net)
        matches[index].append(dict(net=name(net),layer=layer,kind=kind,bbox_dbu=list(map(int,coords))))
    for line in(out/'marker-terminals.tsv').read_text().splitlines():
        kind,net,*values=line.split('\t');assert net in netnames
        if kind=='P':
            assert len(values)==2;row=dict(kind='port',name=name(values[0]),direction=values[1])
        else:
            assert kind=='I'and len(values)==9
            inst,master,term,direction,signal,*box=values
            row=dict(kind='iterm',instance=name(inst),master=name(master),term=name(term),
                     direction=direction,signal_type=signal,instance_bbox_dbu=list(map(int,box)))
        terminals[netnames[net]].append(row)
    counts=(out/'scan-counts.tsv').read_text().split()
    assert len(counts)==3 and all(int(x)>0 for x in counts)
    assert file_sha(odb)==bound['outputs'][str(odb.relative_to(source))]
    assert file_sha(report)==receipt['outputs'][report.name]
    rows=[dict(marker=m,hits=matches[m['index']],candidate_nets=sorted({r['net']for r in matches[m['index']]}))for m in markers]
    result=dict(schema='block-v1-native-drc-location/1',passed=True,
        report_sha256=file_sha(report),source_odb_sha256=file_sha(odb),
        source_receipt_sha256=file_sha(source/'receipt.json'),failed_receipt_sha256=file_sha(failed/'receipt.json'),
        native_geometry_exporter_sha256=file_sha(root/'project/experiments/block_v1/odb_geometry.tcl'),
        marker_count=len(rows),unmatched_markers=[r['marker']['index']for r in rows if not r['hits']],
        markers=rows,terminals=dict(terminals),scanned_nets=int(counts[0]),scanned_shapes=int(counts[1]),hit_shapes=int(counts[2]),
        qualified_hard_macro=False,
        scope='Read-only native wire/via/PG/port rectangle candidates intersecting exact GDS marker envelopes; does not prove polygon ownership, GDS electrical connectivity, gate/diffusion area or repaired DRC')
    (out/'native-drc-location.json').write_text(json.dumps(result,indent=2)+'\n')
