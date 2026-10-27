"""Read-only localization of the actual S final M10 spacing failures."""
import json
from decimal import Decimal
import re


def locate(root,out,cpus,run):
    from io_slots import file_sha
    from five_macro_receive import source
    assert cpus==16
    folder,receipt,_,results=source(out,'s')
    failed=out.parents[2]/'block-v1-20261027-207/tasks/five-macro-drc-s'
    fr=json.loads((failed/'receipt.json').read_text());assert fr['passed']is False
    p=failed/'five-macro-drc.json';assert file_sha(p)==fr['outputs'][p.name]
    failure=json.loads(p.read_text())
    assert failure['source_receipt_sha256']==file_sha(folder/'receipt.json')
    assert failure['full_deck']['total_items']==10 and failure['full_deck']['categories']=={'METAL10.2':10}
    text=failure['native_report']
    expression=r'violation type: ([^\n]+)\n\s*srcs: ([^\n]+)\n\s*bbox = \(([^,]+), ([^)]+)\) - \(([^,]+), ([^)]+)\) on Layer (\w+)\n'
    markers=[];cursor=0
    for match in re.finditer(expression,text):
        assert not text[cursor:match.start()].strip();cursor=match.end()
        category,names,*values,layer=match.groups();values=[Decimal(v)*2000 for v in values]
        assert all(v==int(v)for v in values)and layer=='metal10'
        box=list(map(int,values))
        markers.append(dict(category=category,names=names,layer=layer,reported_box_dbu=box,
                            context_box_dbu=[box[0]-2000,box[1]-2000,box[2]+2000,box[3]+2000]))
    assert len(markers)==7 and not text[cursor:].strip()
    helper=root/'project/experiments/block_v1'
    script='set_thread_count 16\nread_db {'+str(results/'6_final.odb')+'}\nsource {'+str(helper/'odb_geometry.tcl')+'}\n'
    script+='namespace eval bvgeom {variable markers [dict create]}\n'
    for i,m in enumerate(markers):script+='dict lappend bvgeom::markers metal10 {'+str(i)+' '+' '.join(map(str,m['context_box_dbu']))+'}\n'
    script+='source {'+str(helper/'native_drc_locate.tcl')+'}\n'
    (out/'locate.tcl').write_text(script);run(['openroad','-no_init','-exit',str(out/'locate.tcl')],'locate.log')
    hits=[]
    for line in(out/'marker-shapes.tsv').read_text().splitlines():
        index,name,layer,kind,*box=line.split('\t')
        hits.append(dict(marker=int(index),net=bytes.fromhex(name).decode(),layer=layer,kind=kind,box_dbu=list(map(int,box))))
    assert hits and {'addr[6]','addr[7]','din[31]','din[43]','din[55]'}<={h['net']for h in hits}
    assert source(out,'s')[1]==receipt
    result=dict(passed=True,read_only=True,source_receipt_sha256=file_sha(folder/'receipt.json'),
                failure_receipt_sha256=file_sha(failed/'receipt.json'),markers=markers,hits=hits,
                qualified_hard_macro=False,scope='Exact native marker context only; no route or pin edits and no S acceptance.')
    (out/'five-macro-locate-s.json').write_text(json.dumps(result,indent=2)+'\n')
