"""Actual bounded C8 native upper escape edit and independent diagnostic deck."""
import collections
import concurrent.futures
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from native_allocation_group import memory_snapshot,file_sha
from native_c8_legalize import legalize
from native_drc import summarize
from native_escape import records
from native_escape_audit import geometry,connectivity,readback
from native_upper_index import audit


def verify(root,out,cpus,run,policy):
    assert cpus==2 and policy in ('A','C');base=out.parents[2];suffix=policy.lower()
    located=base/'block-v1-20261027-163/tasks'/('native-c8-locate-'+suffix)
    lr=json.loads((located/'receipt.json').read_text());assert lr['passed']is True
    path=located/'native-c8-location.json';assert file_sha(path)==lr['outputs'][path.name]
    proof=json.loads(path.read_text());assert proof['passed']is True and all(v is True for v in proof['checks'].values())
    source=Path(proof['source']);bound=json.loads((source/'receipt.json').read_text());assert bound['passed']is True
    assert file_sha(source/'receipt.json')==proof['source_receipt_sha256']
    folder=source/'flow/results/nangate45'/('bv1_shared109_'+policy)/'base'
    files=[folder/('6_final.'+ext)for ext in ['odb','def','v','sdc','spef']]
    hashes={str(p):file_sha(p)for p in files}
    assert hashes[str(files[0])]==proof['source_odb_sha256']
    assert all(v==bound['outputs'][str(Path(p).relative_to(source))]for p,v in hashes.items())
    names=proof['reported_nets'];assert len(names)==(59 if policy=='A'else 36)
    helper=root/'project/experiments/block_v1';tcl_names=' '.join('{'+n+'}'for n in names)
    setup='set ::env(BV1_GEOMETRY_SOURCE) {%s}\nsource {%s}\n'%(helper/'odb_geometry.tcl',helper/'native_escape_geometry.tcl')
    def execute(name,body):
        (out/(name+'.tcl')).write_text('set_thread_count 2\nread_db {%s}\n'%files[0]+setup+body)
        run(['openroad','-no_init','-exit',name+'.tcl'],name+'.log')
    execute('before','write_def before.def\nwrite_verilog before.v\nescape_geometry before-geometry.tsv {%s}\n'%tcl_names)
    assert file_sha(out/'before-geometry.tsv')==proof['source_geometry_sha256']==lr['outputs']['source-geometry.tsv']
    paths={text.lstrip().split()[1]:text for text in records(out/'before.def')if text.lstrip().split()[1]in names}
    assert paths==proof['source_routes']
    die=None
    with(out/'before.def').open()as stream:
        for line in stream:
            match=re.fullmatch(r'DIEAREA \( (\d+) (\d+) \) \( (\d+) (\d+) \) ;\s*',line)
            if match:die=tuple(map(int,match.groups()));break
    assert die is not None
    before=geometry(out/'before-geometry.tsv');result,texts,plans,predicted=legalize(proof,before,die)
    (out/'routing-preflight.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Bounded obstacle-event preflight failed; no actual edit attempted'
    plans={n:p for n,p in plans.items()if p['changed']};assert plans
    (out/'rewrite-plan.json').write_text(json.dumps(plans,indent=2)+'\n')
    patch='VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\nDESIGN shared109 ;\nUNITS DISTANCE MICRONS 2000 ;\n'
    patch+='NETS %d ;\n'%len(plans)+''.join(texts[n]for n in sorted(plans))+'END NETS\nEND DESIGN\n'
    (out/'escape-patch.def').write_text(patch)
    execute('edit','read_def -floorplan_initialize escape-patch.def\nwrite_def after.def\nwrite_db edited.odb\nwrite_verilog after.v\nescape_geometry after-geometry.tsv {%s}\n'%tcl_names)
    diff=readback(out/'before.def',out/'after.def',plans)
    assert file_sha(out/'before.v')==file_sha(out/'after.v'),'Actual logical/cell netlist changed'
    after=geometry(out/'after-geometry.tsv');assert set(before)==set(after)==set(predicted)
    assert all(collections.Counter(after[n])==collections.Counter(predicted[n])for n in after),'Actual OpenDB rectangles differ from preflight'
    assert all(collections.Counter(before[n])==collections.Counter(after[n])for n in before if n not in plans)
    for name in plans:
        assert collections.Counter(r for r in before[name]if r[0]not in ('metal9','metal10','via9'))==collections.Counter(r for r in after[name]if r[0]not in ('metal9','metal10','via9'))
    source_connections={n:connectivity(before[n])for n in names};final_connections={n:connectivity(after[n])for n in names}
    original_contacts=audit(before);final_contacts=audit(after)
    assert original_contacts['shorts'],'Original full upper short positive control missing'
    cuts={n:connectivity([r for r in after[n]if r[0]!='via9'])for n in plans}
    negative=copy.copy(after);one=next(r for n in plans for r in after[n]if r[0]=='metal10')
    negative['__declared_c8_foreign_short__']=[one];contact_negative=audit(negative)
    run(['klayout','-b','-rd','out='+str(out),'-r',str(helper/'native_c8_gds.rb')],'upper-gds.log')
    native=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc')
    assert file_sha(native)=='4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147'
    tree=ET.parse(native);text=tree.getroot().find('text').text
    helper_rule=re.search(r'(?ms)^def classify_by_width\(.*?^end\n',text).group()
    selected=text[text.index('# metal9\n'):text.index('end # BEOL')]
    assert all(x in selected for x in ['METAL9.2','METAL10.2','VIA9.2'])
    setup='source($in_gds)\nreport("Native C8 upper-layer diagnostic subset",$report_file)\ntiles(1000.um)\ntile_borders(1.um)\ndeep\nthreads(1)\n'
    setup+='metal9=polygons(27,0)\nvia9=polygons(28,0)\nmetal10=polygons(29,0)\n'
    tree.getroot().find('text').text=setup+helper_rule+selected
    deck=out/'upper-only.lydrc';tree.write(deck,encoding='utf-8',xml_declaration=True);reports={}
    for stage in ['before','after']:
        run(['klayout','-b','-rd','in_gds='+str(out/(stage+'-upper.gds')),'-rd','report_file='+str(out/(stage+'-upper.lyrdb')),'-r',str(deck)],stage+'-upper-drc.log')
        reports[stage]=summarize(out/(stage+'-upper.lyrdb'))
    checks=dict(exact_source_geometry=True,faithful_actual_rewrite=diff['passed'],logical_netlist_unchanged=True,
                source_connectivity=all(r['passed']for r in source_connections.values()),edited_connectivity=all(r['passed']for r in final_connections.values()),
                whole_upper_contacts_zero=final_contacts['passed'],missing_cut_controls=all(r['passed']is False for r in cuts.values()),
                declared_foreign_contact_rejected=contact_negative['passed']is False,
                source_native_upper_violations_reproduced=reports['before']['total_items']>0,native_upper_drc_zero=reports['after']['total_items']==0,
                source_unchanged=all(file_sha(Path(p))==h for p,h in hashes.items()))
    record=dict(schema='block-v1-native-c8-probe/1',passed=all(checks.values()),checks=checks,policy=policy,
                source=str(source),source_receipt_sha256=file_sha(source/'receipt.json'),source_files=hashes,
                locator=str(located),locator_receipt_sha256=file_sha(located/'receipt.json'),locator_proof_sha256=file_sha(path),
                die_dbu=die,changes=diff,routing=result,source_connections=source_connections,final_connections=final_connections,
                all_upper_original=original_contacts,all_upper_modified=final_contacts,missing_cut_controls=cuts,native_subset_reports=reports,
                native_full_deck_sha256=file_sha(native),diagnostic_subset_sha256=file_sha(deck),
                edited_odb_sha256=file_sha(out/'edited.odb'),edited_def_sha256=file_sha(out/'after.def'),
                full_native_drc_qualified=False,regenerated_rc_sta_qualified=False,exact_final_function_qualified=False,qualified_hard_macro=False,
                scope='Actual bounded pre-freeze C8 upper edit, exact all-network DEF/cell/geometry identity and independent native upper rule subset only; complete native GDS/DRC, new RC/STA, LEC/final function and macro gates remain mandatory')
    (out/'native-c8-probe.json').write_text(json.dumps(record,indent=2)+'\n')
    assert record['passed'],'Actual C8 upper probe failed; all original and diagnostic evidence retained'


def group(root,out,cpus):
    assert cpus==4
    memory=memory_snapshot();parallel=2 if memory['MemAvailable']>=2*24*1024**3*1.2 else 1
    def execute(policy):
        mode='native-c8-probe-'+policy;folder=out.parent/mode;folder.mkdir(exist_ok=False);start=time.time()
        env=dict(os.environ,OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
        with(folder/'group-child.log').open('w')as stream:
            code=subprocess.run([sys.executable,str(root/'project/experiments/block_v1/worker.py'),str(root),mode,'2'],cwd=folder,env=env,stdout=stream,stderr=subprocess.STDOUT).returncode
        p=folder/'receipt.json';q=folder/'native-c8-probe.json';r=json.loads(p.read_text())if p.exists()else{}
        passed=bool(code==0 and r.get('passed')is True and q.exists())
        if passed:passed=r['cpus']==2 and r['mode']==mode and r['outputs'][q.name]==file_sha(q)and json.loads(q.read_text())['passed']is True
        return dict(policy=policy,cpus=2,started=start,finished=time.time(),passed=passed,returncode=code,
                    receipt_sha256=file_sha(p)if p.exists()else None,proof_sha256=file_sha(q)if q.exists()else None)
    with concurrent.futures.ThreadPoolExecutor(max_workers=parallel)as pool:children=list(pool.map(execute,['a','c']))
    result=dict(schema='block-v1-native-c8-probe-group/1',passed=all(r['passed']for r in children),allocated_cpus=cpus,
                simultaneous_workers=parallel,maximum_concurrent_cpu_ceilings=2*parallel,memory_preflight=memory,
                per_child_memory_budget_bytes=24*1024**3,parallel_memory_safety_factor=1.2,children=children,qualified_hard_macro=False)
    (out/'native-c8-probe-group.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Actual C8 probe child failed; independent peer retained'
