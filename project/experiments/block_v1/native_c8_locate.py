"""Read-only, complete localization of actual final C8 native DRC failures."""
import collections
import concurrent.futures
from decimal import Decimal
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from native_allocation_group import memory_snapshot,file_sha
from native_escape import records,simplify


def markers(text):
    number=r'-?\d+(?:\.\d+)?'
    expression=r'violation type: (Short|Cut Short|Metal Spacing|Cut Spacing)\n\s*srcs: ([^\n]+)\n\s*bbox = \(('+number+'), ('+number+r')\) - \(('+number+'), ('+number+r')\) on Layer (metal(?:[1-9]|10)|via[1-9])\n'
    rows=[];offset=0
    for match in re.finditer(expression,text):
        assert not text[offset:match.start()].strip(),'Unparsed native DRC report content'
        offset=match.end();category,names,*values,layer=match.groups()
        names=names.split();assert names and all(re.fullmatch(r'net:[A-Za-z0-9_]+(?:\[\d+\])?',n)for n in names)
        exact=[Decimal(v)*2000 for v in values];assert all(v==int(v)for v in exact)
        box=list(map(int,exact));assert box[0]<=box[2]and box[1]<=box[3]
        assert category.startswith('Cut')==(layer.startswith('via'))
        rows.append(dict(index=len(rows),category=category,reported_nets=sorted({n[4:]for n in names}),
                         layer=layer,bbox_dbu=[box[0]-1,box[1]-1,box[2]+1,box[3]+1],exact_report_bbox_dbu=box))
    assert rows and not text[offset:].strip(),'Empty or partly parsed native report'
    return rows


def verify(root,out,cpus,run,policy):
    assert cpus==2 and policy in ('A','C');base=out.parents[2];suffix=policy.lower()
    failed=base/'block-v1-20261027-162/tasks'/('native-whole-drc-c8-'+suffix)
    fr=json.loads((failed/'receipt.json').read_text());assert fr['passed']is False
    proof=failed/'native-whole-drc.json';assert file_sha(proof)==fr['outputs'][proof.name]
    p=json.loads(proof.read_text());assert p['passed']is False and p['checks']==dict(source_unchanged=True,checker_geometry_unchanged=True,actual_final_full_chip_native_drc_zero=False)
    report=failed/'native-whole-drc.rpt';assert file_sha(report)==p['report_sha256']==fr['outputs'][report.name]
    source=Path(p['source']);sr=json.loads((source/'receipt.json').read_text());assert sr['passed']is True
    assert file_sha(source/'receipt.json')==p['source_receipt_sha256']
    odb=source/('flow/results/nangate45/bv1_shared109_'+policy+'/base/6_final.odb')
    assert file_sha(odb)==p['source_odb_sha256']==sr['outputs'][str(odb.relative_to(source))]
    rows=markers(report.read_text());assert len(rows)==p['violations']==(49 if policy=='A'else 37)
    names=sorted({n for row in rows for n in row['reported_nets']})
    (out/'markers.json').write_text(json.dumps(rows,indent=2)+'\n')
    helper=root/'project/experiments/block_v1'
    script='set_thread_count 2\nread_db {%s}\nwrite_def source.def\n'%odb
    script+='set ::env(BV1_GEOMETRY_SOURCE) {%s}\nsource {%s}\n'%(helper/'odb_geometry.tcl',helper/'native_escape_geometry.tcl')
    script+='escape_geometry source-geometry.tsv {%s}\n'%' '.join('{'+n+'}'for n in names)
    script+='set stream [open selected-ports.tsv w]\nforeach name {%s} {\n'%' '.join('{'+n+'}'for n in names)
    script+='set net [[ord::get_db_block] findNet $name]\nif {$net eq "NULL"} {error "Missing reported native net"}\n'
    script+='foreach term [$net getBTerms] {foreach pin [$term getBPins] {foreach box [$pin getBoxes] {\n'
    script+='if {[$box isVia]} {error "Unsupported native BPin via geometry"}\n'
    script+='puts $stream "[escape_hex $name]\\t[escape_hex [$term getName]]\\t[$term getIoType]\\t[[$box getTechLayer] getName]\\t[$box xMin]\\t[$box yMin]\\t[$box xMax]\\t[$box yMax]"\n}}}\n}\nclose $stream\n'
    # Restore the original rectangle writer before the independent marker
    # scanner installs its own complete, read-only callback.
    script+='rename bvgeom::rectangle {}\nrename bvgeom::unfiltered_rectangle bvgeom::rectangle\nnamespace eval bvgeom {variable markers [dict create]}\n'
    for row in rows:
        script+='dict lappend bvgeom::markers %s {%d %s}\n'%(row['layer'],row['index'],' '.join(map(str,row['bbox_dbu'])))
    script+='source {%s}\n'%(helper/'native_drc_locate.tcl')
    (out/'locate.tcl').write_text(script);run(['openroad','-no_init','-exit','locate.tcl'],'locate.log')
    hits=collections.defaultdict(list)
    for line in(out/'marker-shapes.tsv').read_text().splitlines():
        i,name,layer,kind,*box=line.split('\t');i=int(i)
        assert 0<=i<len(rows)and layer==rows[i]['layer']and len(box)==4
        hits[i].append(dict(net=bytes.fromhex(name).decode(),layer=layer,kind=kind,bbox_dbu=list(map(int,box))))
    ports=collections.defaultdict(list)
    for line in(out/'selected-ports.tsv').read_text().splitlines():
        name,port,direction,layer,*box=line.split('\t');assert len(box)==4
        ports[bytes.fromhex(name).decode()].append(dict(port=bytes.fromhex(port).decode(),direction=direction,layer=layer,bbox_dbu=list(map(int,box))))
    paths={text.lstrip().split()[1]:text for text in records(out/'source.def')if text.lstrip().split()[1]in names}
    assert set(paths)==set(names)
    proposals={};unsupported={}
    for name in names:
        ps=ports[name]
        if len(ps)!=1 or ps[0]['layer']!='metal10':unsupported[name]='Not exactly one M10 BPin';continue
        box=ps[0]['bbox_dbu'];assert all(v%2==0 for v in [box[0]+box[2],box[1]+box[3]])
        pin=((box[0]+box[2])//2,(box[1]+box[3])//2)
        try:
            text,plan=simplify(paths[name],pin);proposals[name]=dict(plan=plan,proposed_def=text)
        except (AssertionError,ValueError,KeyError)as error:unsupported[name]=str(error)or'Unsupported bounded path grammar/tree'
    for row in rows:
        row['hits']=hits[row['index']];row['candidate_nets']=sorted({v['net']for v in row['hits']})
        row['reported_nets_all_hit']=set(row['reported_nets'])<=set(row['candidate_nets'])
    counts=list(map(int,(out/'scan-counts.tsv').read_text().split()));assert len(counts)==3 and all(n>0 for n in counts)
    checks=dict(all_markers_hit=all(row['hits']for row in rows),all_reported_nets_hit=all(row['reported_nets_all_hit']for row in rows),
                source_unchanged=file_sha(odb)==p['source_odb_sha256'],failure_report_unchanged=file_sha(report)==p['report_sha256'])
    result=dict(schema='block-v1-native-c8-location/1',passed=all(checks.values()),checks=checks,policy=policy,
        source=str(source),source_odb_sha256=p['source_odb_sha256'],source_receipt_sha256=file_sha(source/'receipt.json'),
        failed_source=str(failed),failed_receipt_sha256=file_sha(failed/'receipt.json'),report_sha256=file_sha(report),
        markers=rows,reported_nets=names,ports=dict(ports),source_routes=paths,proposals=proposals,unsupported=unsupported,
        scanned_nets=counts[0],scanned_shapes=counts[1],hit_shapes=counts[2],source_geometry_sha256=file_sha(out/'source-geometry.tsv'),
        qualified_hard_macro=False,scope='Read-only actual native whole-chip DRC localization and bounded fixed-via proposals; no ODB editing, no repaired geometry or complete physical qualification')
    (out/'native-c8-location.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Actual native marker/net localization incomplete; all evidence retained'


def group(root,out,cpus):
    assert cpus==4
    memory=memory_snapshot();simultaneous=2 if memory['MemAvailable']>=2*24*1024**3*1.2 else 1
    def execute(policy):
        mode='native-c8-locate-'+policy;folder=out.parent/mode;folder.mkdir(exist_ok=False);start=time.time()
        env=dict(os.environ,OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
        with(folder/'group-child.log').open('w')as stream:
            code=subprocess.run([sys.executable,str(root/'project/experiments/block_v1/worker.py'),str(root),mode,'2'],cwd=folder,env=env,stdout=stream,stderr=subprocess.STDOUT).returncode
        p=folder/'receipt.json';q=folder/'native-c8-location.json';r=json.loads(p.read_text())if p.exists()else{}
        passed=bool(code==0 and r.get('passed')is True and q.exists())
        if passed:passed=r['cpus']==2 and r['mode']==mode and r['outputs'][q.name]==file_sha(q)and json.loads(q.read_text())['passed']is True
        return dict(policy=policy,cpus=2,started=start,finished=time.time(),passed=passed,returncode=code,
                    receipt_sha256=file_sha(p)if p.exists()else None,proof_sha256=file_sha(q)if q.exists()else None)
    with concurrent.futures.ThreadPoolExecutor(max_workers=simultaneous)as pool:children=list(pool.map(execute,['a','c']))
    result=dict(schema='block-v1-native-c8-location-group/1',passed=all(r['passed']for r in children),allocated_cpus=cpus,
                simultaneous_workers=simultaneous,maximum_concurrent_cpu_ceilings=2*simultaneous,memory_preflight=memory,
                per_child_memory_budget_bytes=24*1024**3,parallel_memory_safety_factor=1.2,children=children,qualified_hard_macro=False)
    (out/'native-c8-location-group.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Read-only C8 location child failed; independent peer retained'
