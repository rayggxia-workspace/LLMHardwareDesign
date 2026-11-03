"""Normalize exact accepted R256 evidence; never rerun or modify issue166.

The new work is an actual complete ODB signal-view export and pin inventory.
Physical/function/formal results remain explicitly attributed to their original
SHA-bound executions. No abstract Liberty qualification is transferred.
"""
import json,os,re,shutil,subprocess,time,sys
from pathlib import Path

PACKAGE=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt252/delivery')
QUAL_SHA='92d6fb1c9cedea11f976bf79ad4da43db0c9af3557e55fca776494f83696b313'
EXPECTED={
 'v':'d7c7442a6b4c9feedbc4b259dac70bd580ee5906c96cfd25aa3a76556733df36',
 'sdc':'46db43d33803f0f88e0efe9e0473fd09804b27f98fc4bc83c1c070f126a4b876',
 'def':'6c0d07b183b6963b5c6677f86255cd0b5b271ce51ae075c51c5caefbcabab4a8',
 'odb':'ae7c3d6df345797bd1cbfcf7422af705f3dd7c938cc875878822b8cfac19fced',
 'spef':'75e921fb755fe1916979196c9be6497c648e71e868030b1762b53ebdd13579e4',
 'gds':'0aeae497fe9014d96e6bde00a9659478572c48344acc7bb2c1ba7b5f32a11119'}


def export_r256(root,out,run,source,receipt,results,top,library):
    """R256 has zero ANTENNA_X1: prove that from actual ODB and full graph.

    Existing control-leaf protection-cell positive checks stay unchanged.
    Every other R signal cell/connection must match the accepted raw netlist.
    """
    from io_slots import file_sha
    from native_logic_projection import project
    from structural_view import compare
    assert top=='r_stream_local'
    odb=results/'6_final.odb';raw=results/'6_final.v'
    assert file_sha(raw)==EXPECTED['v']
    inputs={str(p):file_sha(p)for p in [odb,raw]}
    for p,digest in inputs.items():assert digest==receipt['outputs'][str(Path(p).relative_to(source))]
    target=out/'physical-functional.v'
    script='read_liberty {'+str(library)+'}\nread_db {'+str(odb)+'}\n'
    script+='set remove {}\nforeach lib [[ord::get_db] getLibs] {foreach master [$lib getMasters] {set signal 0;foreach term [$master getMTerms] {if {[$term getSigType] ni {POWER GROUND}} {set signal 1}};if {!$signal} {lappend remove [$master getName]}}}\n'
    script+='set f [open {'+str(out/'actual-protection-count.txt')+'} w]\nset count 0\nforeach inst [[ord::get_db_block] getInsts] {if {[[$inst getMaster] getName] eq "ANTENNA_X1"} {incr count}}\nputs $f $count\nclose $f\nwrite_verilog -remove_cells $remove {'+str(target)+'}\n'
    (out/'physical-functional.tcl').write_text(script);run(['openroad','-no_init','-exit',out/'physical-functional.tcl'],'physical-functional.log')
    assert (out/'actual-protection-count.txt').read_text().strip()=='0'
    parsed={}
    for label,path in [('physical',target),('source',raw)]:
        graph=out/(label+'-functional.json');ys=out/(label+'-functional.ys')
        ys.write_text('read_liberty -lib '+str(library)+'\nread_verilog '+str(path)+'\nhierarchy -check -top '+top+'\nwrite_json '+str(graph)+'\n')
        run(['yosys','-s',ys],label+'-functional-parse.log');parsed[label]=json.loads(graph.read_text())
    physical,proof=project(parsed['physical'],library.read_text());original,oldproof=project(parsed['source'],library.read_text())
    assert proof['removed_count']==oldproof['removed_count']==0
    correspondence=compare(physical,original)
    assert all(file_sha(p)==digest for p,digest in inputs.items())
    result=dict(passed=True,schema='exact-qualified-R256-full-physical-view/1',input_sha256=inputs,full_view=str(target),full_view_sha256=file_sha(target),input_only_projection=proof,source_antenna_count=0,actual_odb_protection_count=0,actual_odb_protection_count_sha256=file_sha(out/'actual-protection-count.txt'),exact_other_signal_connectivity=correspondence,scope='Actual zero-protection-cell R256 ODB export: every signal-bearing cell and pin-bit matches exact accepted raw netlist. No control-leaf protection assertion relaxed.')
    (out/'physical-functional-proof.json').write_text(json.dumps(result,indent=2)+'\n')
    return target,result


def receive(a,root,sha):
    assert os.environ.get('SLURM_JOB_ID')and len(os.sched_getaffinity(0))<=16
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    receipt=dict(passed=False,whole_system_qualified=False,inputs={},commands=[],
        scope='Exact existing R256 standalone qualification normalization and new actual ODB full signal export only; no newly simulated or system result.')
    def bind(p,expected=None):
        p=Path(p);digest=sha(p)
        if expected is not None:assert digest==expected,str(p)
        receipt['inputs'][str(p)]=digest;return digest
    def read(p,expected=None):bind(p,expected);return json.loads(Path(p).read_text())
    def command(cmd,log):
        start=time.time()
        with(a.out/log).open('w')as f:q=subprocess.run(list(map(str,cmd)),cwd=a.out,stdout=f,stderr=subprocess.STDOUT)
        receipt['commands'].append(dict(command=list(map(str,cmd)),log=log,returncode=q.returncode,sha256=sha(a.out/log),seconds=time.time()-start));assert q.returncode==0,log
    try:
        bind(Path(__file__))
        qualification=read(PACKAGE/'QUALIFICATION.json',QUAL_SHA)
        assert qualification['passed']and qualification['native_leaf_qualified']and qualification['capacity']==256
        assert qualification['frequency_mhz']==300 and qualification['state_bytes']==2048
        assert qualification['checks']and all(qualification['checks'].values())
        assert not qualification['hierarchical_lib_timing_qualified']and not qualification['m11_m12_system_qualified']
        original={}
        for path,digest in qualification['evidence'].items():original[path]=read(path,digest)
        evaluation=next(v for p,v in original.items()if p.endswith('/attempt251/evaluation/receipt.json'))
        function=next(v for p,v in original.items()if p.endswith('/attempt119/netlist-queue/receipt.json'))
        assert evaluation['passed']and evaluation['capacity']==256 and all(evaluation['checks'].values())
        assert evaluation['full_deck_items']==0 and all(evaluation['lec']['checks'].values())and all(evaluation['independent_sta']['checks'].values())
        assert function['passed']and len(function['tasks'])==192 and all(v['passed']for v in function['tasks'])
        assert all({v['case']for v in function['tasks']if v['initialization']==i}==set(range(-1,63))for i in range(3))
        files={}
        for suffix,digest in EXPECTED.items():
            source=PACKAGE/'native'/('6_final.'+suffix);bind(source,digest)
            target=a.out/source.name;target.symlink_to(source)
            files[source.name]=dict(path=str(target),sha256=digest,bytes=source.stat().st_size)
        tested=[digest for name,digest in function['inputs'].items()if name.endswith('/6_final.v')]
        assert tested==[EXPECTED['v']]
        for name,digest in [('r_stream_local.sv','dc41d52eb88efe6cc592683b788d09da980c1c01e779ab54db9fb647d730363d'),('r_state_store.sv','7b50c3abae20587ac49726fed375da6390fc1d4a260ae299939fc6725dae1d40')]:
            bind(root/'project/rtl/r_local_state'/name,digest);bind(PACKAGE/'source/rtl'/name,digest)
        native=root/'project/experiments/block_v1';sys.path.insert(0,str(native))
        for name in ['native_signal_view.py','native_logic_projection.py','structural_view.py','io_slots.py']:bind(native/name)
        library=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib');bind(library)
        view,viewproof=export_r256(root,a.out,command,PACKAGE/'native',dict(outputs={'6_final.'+k:v for k,v in EXPECTED.items()}),PACKAGE/'native','r_stream_local',library)
        assert viewproof['passed']
        inventory=PACKAGE/'evidence/physical/physical-pins.tsv';bind(inventory)
        # Match the packaged inventory to the original physically evaluated
        # file; no regenerated pin positions and no snapping to another grid.
        original_inventory=Path(evaluation['physical'])/'physical-pins.tsv';bind(original_inventory,sha(inventory))
        declarations={m.group(4):m.group(1)for m in re.finditer(r'(?m)^\s*(input|output)\s+(?:\[(\d+):(\d+)\]\s+)?(\S+)\s*;',(PACKAGE/'native/6_final.v').read_text())}
        pins=[];seen=set()
        for line in inventory.read_text().splitlines():
            name,layer,*coordinates=line.split('\t');assert name not in seen;seen.add(name)
            box=list(map(int,coordinates));assert layer=='metal10'and len(box)==4
            x,y=(box[0]+box[2])/4000,(box[1]+box[3])/4000
            assert abs(x/4-round(x/4))<1e-8 and abs(y/4-round(y/4))<1e-8
            match=re.fullmatch(r'([A-Za-z_][A-Za-z_0-9]*)(?:\[(\d+)\])?',name);assert match
            port,index=match.groups();assert port in declarations
            pins.append(dict(pin=name,port=port,index=int(index or 0),direction=declarations[port],layer=layer,box_dbu=box,xy_um=[x,y],size_um=[(box[2]-box[0])/2000,(box[3]-box[1])/2000],role='clock'if name=='clk'else'reset'if name=='reset'else'signal',region='internal'))
        assert len(pins)==821
        (a.out/'pins.json').write_text(json.dumps(dict(schema='block-v1-pin-plan/1',policy='exact-qualified-R256-native-inventory',pins=pins),indent=2)+'\n')
        gate_reports={
          'physical':dict(checks=evaluation['checks'],active_area_um2=evaluation['metrics']['finish__design__instance__area__stdcell']),
          'drc':dict(full_deck=dict(total_items=evaluation['full_deck_items']),native_report=(PACKAGE/'evidence/physical/native-whole-drc.rpt').read_text()),
          'function':dict(full_final_netlist=viewproof,original_192_case_result=function),
          'formal':dict(strict_native_lec=evaluation['lec'])}
        assert not gate_reports['drc']['native_report'].strip()
        gates={}
        for operation,report in gate_reports.items():
            name={'physical':'five-macro-physical.json','drc':'five-macro-drc.json','function':'final-function.json','formal':'formal.json'}[operation]
            folder=a.out/'reused-gates'/operation;folder.mkdir(parents=True)
            report.update(passed=True,source_receipt_sha256=QUAL_SHA,reused_existing_exact_evidence=True,original_qualification=str(PACKAGE/'QUALIFICATION.json'),original_evidence=qualification['evidence'],scope='Normalized exact existing standalone R256 evidence; no newly executed '+operation+' result.')
            (folder/name).write_text(json.dumps(report,indent=2)+'\n')
            (folder/'receipt.json').write_text(json.dumps(dict(passed=True,operation='exact-existing-R256-'+operation,inputs=dict(receipt['inputs']),outputs={name:sha(folder/name)},reused_existing_exact_evidence=True,whole_system_qualified=False),indent=2)+'\n')
            gates[operation]=dict(path=str(folder/'receipt.json'),sha256=sha(folder/'receipt.json'),report_sha256=sha(folder/name))
        image=PACKAGE/'native/layout.png';bind(image);shutil.copyfile(image,a.out/'layout.png')
        delivery=dict(passed=True,native_leaf_accepted=True,top='r_stream_local',source_receipt_sha256=QUAL_SHA,gate_receipts=gates,final_files=files,die_um=[1000,1000],active_area_um2=gate_reports['physical']['active_area_um2'],image_sha256=sha(a.out/'layout.png'),pins_sha256=sha(a.out/'pins.json'),reused_existing_exact_R256_qualification=True,complete_system_qualified=False,m11_m12_system_qualified=False)
        (a.out/'delivery.json').write_text(json.dumps(delivery,indent=2)+'\n')
        row=dict(final_files=files,pins=str(a.out/'pins.json'),pins_sha256=sha(a.out/'pins.json'),die_um=[1000,1000],placement_phase_um=[.095,.07])
        (a.out/'physical.json').write_text(json.dumps(dict(leaves={'r_stream_local':row},whole_system_qualified=False),indent=2)+'\n')
        receipt.update(passed=True,existing_native_leaf_qualification_reused=True,new_actual_complete_signal_view_export=True,new_original_pin_inventory_binding=True)
    finally:
        receipt['outputs']={str(p.relative_to(a.out)):sha(p)for p in a.out.rglob('*')if p.is_file()}
        (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
