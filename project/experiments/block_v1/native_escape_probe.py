"""Two-candidate bounded native route edit probe, with explicit remaining gates."""
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
from io_slots import file_sha
from native_allocation_group import memory_snapshot
from native_drc import summarize
from native_escape import parse,simplify,records
from native_escape_audit import geometry,physical,connectivity,readback


def verify(root,out,cpus,run,policy):
    assert cpus==2 and policy in ('A','C')
    base=out.parents[2];suffix=policy.lower()
    source=base/'block-v1-20261027-133/tasks'/('native-viaonly-run-transaction6k-'+suffix)
    bound=json.loads((source/'receipt.json').read_text());assert bound['passed']is True
    folder=source/'flow/results/nangate45'/('bv1_transaction6k_'+policy)/'base'
    files=[folder/('6_final.'+ext)for ext in ['odb','def','v','sdc','spef']]
    hashes={str(p):file_sha(p)for p in files}
    assert all(v==bound['outputs'][str(Path(p).relative_to(source))]for p,v in hashes.items())
    failed=base/'block-v1-20261027-135/tasks'/('native-viaonly-receive-transaction6k-'+suffix)
    receipt=json.loads((failed/'receipt.json').read_text());assert receipt['passed']is False
    path=failed/'native-physical-receiver.json';assert file_sha(path)==receipt['outputs'][path.name]
    gates=json.loads(path.read_text());assert gates['source']==str(source)and gates['source_receipt_sha256']==file_sha(source/'receipt.json')
    assert gates['checks']['independent_native_drc_zero']is False
    assert all(v for k,v in gates['checks'].items()if k!='independent_native_drc_zero')
    native_gds=failed/'gds-flow/results/nangate45'/('bv1_transaction6k_'+policy)/'base/6_final.gds'
    assert file_sha(native_gds)==gates['gds_sha256']
    located=base/'block-v1-20261027-148/tasks'/('native-viaonly-drc-locate-'+suffix)
    lr=json.loads((located/'receipt.json').read_text());assert lr['passed']is True
    path=located/'native-drc-location.json';assert file_sha(path)==lr['outputs'][path.name]
    location=json.loads(path.read_text());assert location['source_odb_sha256']==hashes[str(files[0])]
    assert location['failed_receipt_sha256']==file_sha(failed/'receipt.json')and not location['unmatched_markers']
    names=sorted({name for row in location['markers']for name in row['candidate_nets']})
    assert names and all(re.fullmatch(r'[A-Za-z0-9_]+(?:\[\d+\])?',n)for n in names)
    prep=base/'block-v1-20261027-077/tasks/native-prepare';pr=json.loads((prep/'receipt.json').read_text());assert pr['passed']is True
    pins_path=prep/('transaction6k-'+policy)/'pins.json'
    assert file_sha(pins_path)==pr['outputs'][str(pins_path.relative_to(prep))]
    pins={p['pin']:tuple(round(x*2000)for x in p['xy_um'])for p in json.loads(pins_path.read_text())['pins']}
    assert set(names)<=set(pins)
    paths={text.lstrip().split()[1]:text for text in records(files[1])if text.lstrip().split()[1]in names}
    assert set(paths)==set(names)
    plans={};rewritten={}
    for name in names:
        text,plan=simplify(paths[name],pins[name])
        if plan['changed']:
            plan['header']=parse(paths[name])[0];plans[name]=plan;rewritten[name]=text
    assert plans
    (out/'rewrite-plan.json').write_text(json.dumps(plans,indent=2)+'\n')
    tcl_names=' '.join('{'+n+'}'for n in names)
    helper='set ::env(BV1_GEOMETRY_SOURCE) {%s}\nsource {%s}\n'%(root/'project/experiments/block_v1/odb_geometry.tcl',root/'project/experiments/block_v1/native_escape_geometry.tcl')
    def script(name,body):
        (out/(name+'.tcl')).write_text('set_thread_count 2\nread_db {%s}\n'%files[0]+helper+body)
        run(['openroad','-no_init','-exit',name+'.tcl'],name+'.log')
    script('before','write_def before.def\nwrite_verilog before.v\nescape_geometry before-geometry.tsv {%s}\n'%tcl_names)
    patch='VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\nDESIGN transaction6k ;\nUNITS DISTANCE MICRONS 2000 ;\n'
    patch+='NETS %d ;\n'%len(rewritten)+''.join(rewritten.values())+'END NETS\nEND DESIGN\n'
    (out/'escape-patch.def').write_text(patch)
    edit=''
    for name in plans:
        edit+='set net [[ord::get_db_block] findNet {%s}]\nif {$net eq "NULL" || [$net getWire] eq "NULL"} {error "Missing source net/wire"}\n'%name
    # INCREMENTAL intentionally omits the NETS callbacks in definReader.
    # FLOORPLAN processes only these existing named nets and replaces wires;
    # all actual definitions, other nets and geometry are checked below.
    edit+='read_def -floorplan_initialize escape-patch.def\nwrite_def after.def\nwrite_db edited.odb\nwrite_verilog after.v\nescape_geometry after-geometry.tsv {%s}\n'%tcl_names
    script('edit',edit)
    diff=readback(out/'before.def',out/'after.def',plans)
    assert file_sha(out/'before.v')==file_sha(out/'after.v'),'Cell/logical netlist changed'
    before=geometry(out/'before-geometry.tsv');after=geometry(out/'after-geometry.tsv')
    assert set(before)==set(after)
    unchanged=[name for name in before if name not in plans]
    assert all(sorted(before[n])==sorted(after[n])for n in unchanged),'Other net geometry changed'
    for name in plans:
        assert sorted(r for r in before[name]if r[0]not in ('metal9','metal10','via9'))==sorted(r for r in after[name]if r[0]not in ('metal9','metal10','via9'))
    original=physical(before,names);modified=physical(after,names)
    controls={}
    for name in plans:
        cut=[r for r in after[name]if r[0]!='via9']
        broken=connectivity(cut);assert broken['passed']is False
        controls[name]=broken
    negative=copy.copy(after);one=next(r for n in plans for r in after[n]if r[0]=='metal10')
    negative['__declared_cross_net_short__']=[one]
    short_control=physical(negative,names);assert short_control['cross_net_shorts']and not short_control['passed']
    run(['klayout','-b','-rd','out='+str(out),'-rd','source_gds='+str(native_gds),'-r',str(root/'project/experiments/block_v1/native_escape_gds.rb')],'upper-gds.log')
    native=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc')
    assert file_sha(native)=='4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147'
    tree=ET.parse(native);text=tree.getroot().find('text').text
    helper_rule=re.search(r'(?ms)^def classify_by_width\(.*?^end\n',text).group()
    selected=text[text.index('# metal9\n'):text.index('end # BEOL')]
    assert all(x in selected for x in ['METAL9.2','METAL10.2','VIA9.2'])
    setup='source($in_gds)\nreport("Native upper-layer diagnostic subset",$report_file)\ntiles(1000.um)\ntile_borders(1.um)\ndeep\nthreads(1)\n'
    setup+='metal9=polygons(27,0)\nvia9=polygons(28,0)\nmetal10=polygons(29,0)\n'
    # Exact native rule bodies for M9/via9/M10, on complete actual ODB masks.
    # This new diagnostic deck does not replace or alter the full receiver.
    tree.getroot().find('text').text=setup+helper_rule+selected
    deck=out/'upper-only.lydrc';tree.write(deck,encoding='utf-8',xml_declaration=True)
    reports={}
    for stage in ['before','after']:
        # Reproduce the full native report on its exact unmerged native GDS.
        # Merged mask unions are independently XOR-equal but may coalesce
        # duplicate edge-pair reports; their raw item count is not invariant.
        gds=native_gds if stage=='before'else out/'after-upper.gds'
        run(['klayout','-b','-rd','in_gds='+str(gds),'-rd','report_file='+str(out/(stage+'-upper.lyrdb')),'-r',str(deck)],stage+'-upper-drc.log')
        reports[stage]=summarize(out/(stage+'-upper.lyrdb'))
        reports[stage]['scope']='Unchanged native M9/via9/M10 rule bodies only, on exact original full GDS before or actual edited upper union after; no full physical qualification'
    checks=dict(exact_def_scope=diff['passed'],logical_netlist_unchanged=True,source_connectivity=all(r['passed']for r in original['nets'].values()),
        original_real_spacing_reproduced=bool(original['base_spacing_under_800nm']),
        full_native_source_markers_reproduced=reports['before']['total_items']==gates['independent_drc_items']and reports['before']['categories']==gates['independent_drc_categories'],
        exact_full_native_upper_mask_identity=True,
        edited_geometry=modified['passed'],missing_cut_controls=all(not x['passed']for x in controls.values()),
        real_cross_net_short_rejected=not short_control['passed'],native_upper_drc_zero=reports['after']['total_items']==0)
    assert all(file_sha(Path(p))==v for p,v in hashes.items())and file_sha(native_gds)==gates['gds_sha256'],'Sealed source changed'
    result=dict(schema='block-v1-native-escape-probe/1',passed=all(checks.values()),checks=checks,policy=policy,
        source=str(source),source_receipt_sha256=file_sha(source/'receipt.json'),failed_receiver_receipt_sha256=file_sha(failed/'receipt.json'),
        locator_receipt_sha256=file_sha(located/'receipt.json'),source_files=hashes,plans=plans,def_readback=diff,
        original_physical=original,edited_physical=modified,missing_cut_controls=controls,
        actual_cross_net_short_count=len(short_control['cross_net_shorts']),native_subset_reports=reports,
        original_full_native_gds=str(native_gds),original_full_native_gds_sha256=gates['gds_sha256'],
        mask_readback=json.loads((out/'upper-mask-readback.json').read_text()),
        native_full_deck_sha256=file_sha(native),diagnostic_subset_sha256=file_sha(deck),
        edited_odb_sha256=file_sha(out/'edited.odb'),edited_def_sha256=file_sha(out/'after.def'),
        full_native_drc_qualified=False,regenerated_rc_sta_qualified=False,exact_final_function_qualified=False,qualified_hard_macro=False,
        scope='Bounded pre-freeze M9/M10/via9 escape edit and actual same-source geometry/upper-mask tests only; full native GDS/DRC, regenerated RC/STA, exact final function and all macro/twelve-layer gates remain required')
    (out/'native-escape-probe.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Bounded escape geometry gate failed; preserve source and complete output'


def group(root,out,cpus):
    assert cpus==4
    memory=memory_snapshot();parallel=2 if memory['MemAvailable']>=12*1024**3 else 1
    def execute(policy):
        mode='native-escape-probe-'+policy;folder=out.parent/mode;folder.mkdir(exist_ok=False)
        started=time.time();env=dict(os.environ,OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
        with(folder/'group-child.log').open('w')as stream:
            code=subprocess.run([sys.executable,str(root/'project/experiments/block_v1/worker.py'),str(root),mode,'2'],cwd=folder,env=env,stdout=stream,stderr=subprocess.STDOUT).returncode
        p=folder/'receipt.json';q=folder/'native-escape-probe.json';r=json.loads(p.read_text())if p.exists()else{}
        passed=bool(code==0 and r.get('passed')is True and q.exists())
        if passed:passed=r['cpus']==2 and r['mode']==mode and r['outputs'][q.name]==file_sha(q)and json.loads(q.read_text())['passed']is True
        return dict(policy=policy,cpus=2,started=started,finished=time.time(),returncode=code,passed=passed,
            receipt_sha256=file_sha(p)if p.exists()else None,proof_sha256=file_sha(q)if q.exists()else None)
    with concurrent.futures.ThreadPoolExecutor(max_workers=parallel)as pool:children=list(pool.map(execute,['a','c']))
    result=dict(schema='block-v1-native-escape-group/1',passed=all(r['passed']for r in children),children=children,
        allocated_cpus=cpus,maximum_concurrent_cpu_ceilings=2*parallel,memory_preflight=memory,
        scope='Two bounded actual escape geometry probes; independent peer completes after failure; no complete physical or macro qualification')
    (out/'native-escape-group.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],'Escape probe failed; peer evidence retained'
