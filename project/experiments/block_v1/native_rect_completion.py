"""Complete the installed path iterator's missing RECTs from sealed native DEF.

The installed Tcl binding does not expose dbWireShapeItr. Native DEF writes
the RECTs; accepted GDS/DRC and the original native DB remain unchanged.
"""
from collections import Counter
import json
from pathlib import Path
import re
import shutil


def rectangles(record):
    route=re.search(r'\+\s+(?:ROUTED|FIXED|COVER)\s+',record)
    if route is None:return []
    name=record.lstrip().split()[1];result=[]
    body=record[route.end():].strip().removesuffix(';').strip()
    for path in re.split(r'\s+NEW\s+',body):
        if not re.search(r'\bRECT\b',path):continue
        # The actual installed DEF writer emits patch rectangles on anchored
        # paths. Fail rather than interpreting an unsupported RECT grammar.
        integer=r'(-?\d+)'
        box=r'RECT\s*\(\s*'+r'\s+'.join([integer]*4)+r'\s*\)'
        pattern=r'(metal(?:[1-9]|10))\s*\(\s*'+integer+r'\s+'+integer+r'\s*\)\s*((?:'+box+r'\s*)+)'
        match=re.fullmatch(pattern,path.strip());assert match,'Unsupported native RECT path: '+path
        layer,x,y,rest=match.groups()[:4];x=int(x);y=int(y)
        for m in re.finditer(box,rest):
            a,b,c,d=map(int,m.groups());assert a<c and b<d
            result.append((name,layer,x+a,y+b,x+c,y+d))
    assert len(result)==len(re.findall(r'\bRECT\b',body))
    return result


def complement(geometry,source_def,kind):
    from io_slots import file_sha
    from native_escape import records
    aliases={};before_counts=Counter()
    with geometry.open()as stream:
        for line in stream:
            if line.startswith('# NET n'):
                _,_,alias,encoded=line.split();name=bytes.fromhex(encoded).decode()
                assert name not in aliases;aliases[name]=alias
            elif not line.startswith('#'):
                before_counts[line.split('\t')[2]]+=1
    assert not before_counts['wire-rect'],'RECT complement must run exactly once'
    expected=[]
    for record in records(source_def):
        expected.extend(rectangles(record))
    if kind=='m':
        assert ('$abc$226431$new_n33888','metal2',282460,530600,282650,531160)in expected
    rendered=[]
    for name,layer,a,b,c,d in expected:
        if name not in aliases:
            name=re.sub(r'\\(.)',r'\1',name)
        assert name in aliases,'Unresolved native RECT net identity'
        rendered.append((aliases[name],layer,a,b,c,d))
    with geometry.open('a')as stream:
        for net,layer,a,b,c,d in rendered:
            stream.write(f'{net}\t{layer}\twire-rect\t{a}\t{b}\t{c}\t{d}\n')
    observed=Counter()
    with geometry.open()as stream:
        for line in stream:
            if line.startswith('#'):continue
            net,layer,typ,*box=line.rstrip('\n').split('\t')
            if typ=='wire-rect':observed[(net,layer,*map(int,box))]+=1
    assert observed==Counter(rendered)
    sample='- example\n + ROUTED metal2 ( 282580 531020 ) RECT ( -120 -420 70 140 ) ;\n'
    assert rectangles(sample)==[('example','metal2',282460,530600,282650,531160)]
    refused=False
    try:rectangles(sample.replace('( 282580 531020 )','( * 531020 )'))
    except AssertionError:refused=True
    assert refused
    # A missing, extra or reassigned complement cannot satisfy the exact
    # independently parsed native-DEF multiset.
    fixture=Counter({('n1','metal2',282460,530600,282650,531160):1})
    assert Counter()!=fixture
    assert Counter({('n2','metal2',282460,530600,282650,531160):1})!=fixture
    return dict(passed=True,native_def_path=str(source_def),native_def_sha256=file_sha(source_def),
                rectangle_count=len(expected),rectangles=expected,exact_rect_multiset=True,
                known_m_gds_patch_present=kind=='m',unsupported_rect_path_rejected=refused,
                scope='All normal-net RECT tokens in sealed native DEF parsed or rejected; append them to the installed path-iterator geometry under exact native net identity. No source DB/GDS edits.')


def complete(root,out,cpus,run,kind):
    from five_macro_geometry import accepted
    from io_slots import file_sha,slot
    assert cpus==16 and kind in ('m','t')
    index,odb,provenance,count,die=accepted(root,out,kind)
    old=out.parents[2]/('block-v1-20261027-'+('216'if kind=='m'else'217'))/'tasks'/('five-macro-geometry-'+kind)
    r=json.loads((old/'receipt.json').read_text());assert r['passed']and r['mode']=='five-macro-geometry-'+kind
    p=old/'five-macro-geometry.json';assert file_sha(p)==r['outputs'][p.name]
    previous=json.loads(p.read_text());assert previous['passed']and previous['source_odb_sha256']==file_sha(odb)
    assert previous['geometry_helper_sha256']==file_sha(root/'project/experiments/block_v1/odb_geometry.tcl')
    source_def=Path(index['final_files']['6_final.def']['path'])
    assert file_sha(source_def)==index['final_files']['6_final.def']['sha256']
    with slot(out.parents[2]):
        for name,entry in previous['files'].items():
            src=Path(entry['path']);assert file_sha(src)==entry['sha256']==r['outputs'][name]
            shutil.copyfile(src,out/name);assert file_sha(out/name)==entry['sha256']
    proof=complement(out/'source-occupancy.tsv',source_def,kind)
    (out/'native-rect-completion.json').write_text(json.dumps(proof,indent=2)+'\n')
    counts=Counter();layers=Counter()
    with(out/'source-occupancy.tsv').open()as stream:
        for line in stream:
            if line.startswith('#'):continue
            _,layer,typ,*box=line.rstrip('\n').split('\t');a,b,c,d=map(int,box);assert a<c and b<d
            counts[typ]+=1;layers[layer]+=1
    assert counts==Counter(previous['native_geometry_counts'])+Counter({'wire-rect':proof['rectangle_count']})
    assert file_sha(odb)==previous['source_odb_sha256']
    files={}
    for name in list(previous['files'])+['native-rect-completion.json']:
        p=out/name;files[name]=dict(path=str(p),sha256=file_sha(p),bytes=p.stat().st_size)
    result=dict(previous,files=files,provenance=provenance,native_geometry_counts=dict(counts),
                native_layer_counts=dict(layers),native_def_rect_complete=True,rect_completion=proof,
                iterator_export_receipt_path=str(old/'receipt.json'),iterator_export_receipt_sha256=file_sha(old/'receipt.json'),
                scope='Read-only complete native geometry: installed path-iterator wire/via/PG/pin/OBS plus all sealed native-DEF normal-net RECTs. Candidate LEF coverage, hierarchical timing and M11/M12 system qualification remain false.')
    (out/'five-macro-geometry.json').write_text(json.dumps(result,indent=2)+'\n')
