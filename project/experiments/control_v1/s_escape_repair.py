"""S1181-only, source-bound pre-freeze M10 escape repair and fresh final RC.

The reusable escape planner/readback is unchanged. No cell, port, via or
non-target net may change. All native/function/formal/PG gates remain separate.
"""
import copy,json,os,re,shutil,subprocess,sys,time
from pathlib import Path
from native_s_output import sha

ROOT=Path(__file__).resolve().parents[3]
REL=Path('flow/results/nangate45/bv1_block_feed_s_macro/base')
TARGET='dout[58]'


def check_final_plan(text):
    calls=re.findall(r'/OpenROAD-flow-scripts/flow/scripts/flow\.sh\s+(\S+)\s+(\S+)',text)
    assert calls==[('6_report','final_report')],calls
    assert not any(token in text for token in ['synth.sh','global_place.tcl','floorplan.tcl','cts.tcl','-- do-5_'])


def vertical_plan(text,pin):
    """Other shortest L: avoid the observed notch beside the fixed 2um pin."""
    from native_escape import simplify,emit,signature,path_length
    candidate,plan=simplify(text,pin)
    assert plan['changed'] and plan['kind']=='anchored-m10-shortest-L'
    assert tuple(pin)==(1760190,840140) and tuple(plan['original_via9_dbu'])==(1756990,848140)
    anchor=tuple(plan['original_via9_dbu']);bend=(pin[0],anchor[1])
    original=plan['final_paths']
    paths=[p for p in original if p['layer']!='metal10' or p['via']is not None]
    paths += [dict(layer='metal10',points=[(*pin,0),(*bend,None)],via=None),
              dict(layer='metal10',points=[(*bend,None),(*anchor,None)],via=None)]
    assert signature(paths)!=signature(original)
    assert path_length(paths,'metal10')==path_length(original,'metal10')==11200
    plan.update(kind='S1181-fixed-pin-vertical-first-shortest-L',final_paths=paths)
    from native_escape import parse
    return emit(parse(text)[0],paths),plan


def audit(raw,flow,receipt,file_sha=sha):
    binding=flow['S_prefreeze_escape_repair']
    assert flow['top']=='block_feed_s_macro' and binding['physical_owner']=='block_feed_s_macro M1-M10'
    proof=raw/'s-escape-proof.json';assert file_sha(proof)==binding['proof_sha256']==receipt['outputs'][proof.name]
    p=json.loads(proof.read_text());assert p['passed'] and p['changed_nets']==[TARGET]
    assert p['helper_sha256']==file_sha(Path(__file__))
    prior=Path(p['source']);old=json.loads((prior/'receipt.json').read_text())
    assert old['passed'] and file_sha(prior/'receipt.json')==p['source_receipt_sha256']
    for name,digest in p['source_files'].items():assert file_sha(name)==digest
    sys.path.insert(0,str(ROOT/'project/experiments/block_v1'))
    from native_escape_audit import readback,def_inventory
    assert readback(raw/'before.def',raw/'edited.def',p['plans'])['passed']
    assert file_sha(raw/'before.v')==file_sha(raw/'edited.v')==file_sha(raw/'final-all.v')
    assert def_inventory(raw/'edited.def')==def_inventory(raw/'final-readback.def')
    assert file_sha(raw/'final-readback.def')==file_sha(raw/'checked-readback.def')
    assert not(raw/'native-router-drc.rpt').read_text().strip()
    assert file_sha(raw/REL/'6_final.sdc')==file_sha(prior/REL/'6_final.sdc')
    assert file_sha(raw/'original.odb')==p['source_files'][str(prior/REL/'6_final.odb')]
    assert file_sha(raw/'edited.odb')==p['edited_odb_sha256']
    for name in ['before.def','edited.def','before.v','edited.v','final-all.v','final-readback.def','checked-readback.def','native-router-drc.rpt','escape-patch.def']:
        assert file_sha(raw/name)==receipt['outputs'][name]


def implement(a):
    assert os.environ.get('SLURM_JOB_ID') and len(os.sched_getaffinity(0))<=16
    base=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162')
    prior=a.s_native_source.resolve();failure=a.s_escape_drc.resolve();out=a.out.resolve()
    assert base in prior.parents and base in failure.parents and base in out.parents
    assert prior==base/'s-internal-drive-02/candidate-1181'
    assert failure==base/'s-final-evidence-02/1181/drc'
    out.mkdir(parents=True,exist_ok=False)
    r=dict(passed=False,top='block_feed_s_macro',inputs={},commands=[],job=os.environ['SLURM_JOB_ID'],
           native_leaf_accepted=False,whole_system_qualified=False)
    def bind(path,expected=None):
        value=sha(path)
        if expected is not None:assert value==expected,(str(path),value,expected)
        r['inputs'][str(path)]=value;return value
    def run(command,log):
        command=list(map(str,command));start=time.time()
        with(out/log).open('w')as stream:q=subprocess.run(command,cwd=out,stdout=stream,stderr=subprocess.STDOUT)
        r['commands'].append(dict(command=command,log=log,sha256=sha(out/log),returncode=q.returncode,seconds=time.time()-start))
        assert q.returncode==0,(log,q.returncode)
    try:
        old=json.loads((prior/'receipt.json').read_text());assert old['passed'] and old['native_pipeline_completed']
        bind(prior/'receipt.json');flow=json.loads((prior/'native-flow.json').read_text());bind(prior/'native-flow.json',old['outputs']['native-flow.json'])
        assert flow['top']=='block_feed_s_macro' and flow['passed'] and flow['pipeline_completed']
        failed=json.loads((failure/'receipt.json').read_text());assert failed['passed'] is False
        bind(failure/'receipt.json');report=(failure/'native-whole-drc.rpt').read_text();bind(failure/'native-whole-drc.rpt')
        assert report.count('violation type:')==4 and report.count('violation type: Metal Spacing')==4
        assert report.count('srcs: net:'+TARGET)==4 and report.count('on Layer metal10')==4
        gate=failure.parent/'physical';physical=json.loads((gate/'receipt.json').read_text());assert physical['passed']
        bind(gate/'receipt.json');assert physical['producer_receipt_sha256']==sha(prior/'receipt.json')
        assert failed['producer_receipt_sha256']==sha(prior/'receipt.json')
        # The first shortest L created a 0.2um notch beside the fixed BPin.
        # Preserve its actual failed full-native result and try the other L;
        # no width/spacing rule or pin is changed to hide that failure.
        previous=base/'s-escape-repair-01/candidate-1330'
        previous_receipt=json.loads((previous/'receipt.json').read_text());assert previous_receipt['passed']is False
        bind(previous/'receipt.json')
        notch=(previous/'preflight-native-drc.rpt').read_text();bind(previous/'preflight-native-drc.rpt',previous_receipt['outputs']['preflight-native-drc.rpt'])
        assert notch.count('violation type:')==1 and 'srcs: net:'+TARGET in notch and 'on Layer metal10'in notch
        assert 'bbox = (878.8950, 419.6700) - (879.0950, 421.0700)'in notch
        for path,digest in old['inputs'].items():bind(path,digest)
        for name,digest in flow['rtl_sha256'].items():bind(ROOT/name,digest)
        sys.path.insert(0,str(ROOT/'project/experiments/block_v1'))
        from native_escape import records,parse
        from native_escape_audit import readback,def_inventory
        for name in ['native_escape.py','native_escape_audit.py']:bind(ROOT/'project/experiments/block_v1'/name)
        source_files={}
        def copy_file(source,dest):
            digest=bind(source,old['outputs'][str(source.relative_to(prior))]);source_files[str(source)]=digest
            dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest);assert sha(dest)==digest
        for path in prior.iterdir():
            if path.is_file()and(path.name in ['input.v','input.sdc','pins.json','config.mk']or path.suffix in ['.lef','.tcl']):copy_file(path,out/path.name)
        copy_file(prior/REL/'6_final.odb',out/'original.odb')
        results=out/REL;results.mkdir(parents=True)
        for name in ['1_synth_lec.v','1_2_yosys.v','1_2_yosys.sdc','bv1-input-diodes.tsv','feed-input-receivers.tsv','feed-partition-fanout.tsv','strong-output-drivers.tsv']:
            copy_file(prior/REL/name,results/name)
        copy_file(prior/REL/'6_final.sdc',results/'6_1_fill.sdc')
        for category in ['logs','reports','objects']:(out/'flow'/category/'nangate45/bv1_block_feed_s_macro/base').mkdir(parents=True)
        mk=(prior/'config.mk').read_text().replace(str(prior),str(out));(out/'config.mk').write_text(mk)
        def execute(name,body,odb='original.odb'):
            path=out/(name+'.tcl');path.write_text('set_thread_count 16\nread_db {'+str(out/odb)+'}\n'+body)
            run(['openroad','-no_init','-exit',path],name+'.log')
        checkpoint=a.s_escape_checkpoint
        if checkpoint:
            checkpoint=checkpoint.resolve();assert checkpoint==base/'s-escape-repair-01/candidate-1340'
            prepared=json.loads((checkpoint/'receipt.json').read_text());assert prepared['passed']is False
            bind(checkpoint/'receipt.json')
            assert prepared['inputs'][str(prior/'receipt.json')]==sha(prior/'receipt.json')
            assert prepared['commands'][-1]['log']=='finish-plan.log' and prepared['commands'][-1]['returncode']==0
            check=[c for c in prepared['commands']if c['log']=='preflight-drc.log'];assert len(check)==1 and check[0]['returncode']==0
            for name in ['before.def','before.v','edited.def','edited.v','edited.odb','escape-patch.def','preflight-drc.log','preflight-native-drc.rpt','finish-plan.log']:
                bind(checkpoint/name,prepared['outputs'][name]);shutil.copyfile(checkpoint/name,out/name)
            assert sha(checkpoint/'original.odb')==sha(out/'original.odb')
            assert not(out/'preflight-native-drc.rpt').read_text().strip()
            r['reused_preparation']=dict(source=str(checkpoint),receipt_sha256=sha(checkpoint/'receipt.json'),
                scope='Only exact vertical-L geometry and successful zero complete-native preflight reused; failed preparation has no native/function/formal/PG qualification')
        else:execute('before','write_def before.def\nwrite_verilog before.v\n')
        pins={p['pin']:tuple(round(x*2000)for x in p['xy_um'])for p in json.loads((out/'pins.json').read_text())['pins']}
        selected=[text for text in records(out/'before.def')if text.lstrip().split()[1]==TARGET];assert len(selected)==1
        candidate,plan=vertical_plan(selected[0],pins[TARGET]);assert plan['changed'];plan['header']=parse(selected[0])[0]
        patch=out/'escape-patch.def';expected_patch='VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\nDESIGN block_feed_s_macro ;\nUNITS DISTANCE MICRONS 2000 ;\nNETS 1 ;\n'+candidate+'END NETS\nEND DESIGN\n'
        if checkpoint:assert patch.read_text()==expected_patch
        else:
            patch.write_text(expected_patch)
            execute('edit','read_def -floorplan_initialize {'+str(patch)+'}\nwrite_def edited.def\nwrite_verilog edited.v\nwrite_db edited.odb\n')
        plans={TARGET:plan};proof=readback(out/'before.def',out/'edited.def',plans)
        assert sha(out/'before.v')==sha(out/'edited.v')
        if not checkpoint:execute('preflight-drc','drt::check_drc_cmd preflight-native-drc.rpt 0 0 0 0 s_escape_drc\n','edited.odb')
        assert not(out/'preflight-native-drc.rpt').read_text().strip(),'Edited complete-native DRC failed; no expensive final reporting attempted'
        shutil.copyfile(out/'edited.odb',results/'6_1_fill.odb')
        new=copy.deepcopy(flow);new.update(passed=False,pipeline_completed=False,final_files={},config_sha256=sha(out/'config.mk'))
        command=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(out/'config.mk'),'WORK_HOME='+str(out/'flow'),'NUM_CORES=16']
        expected={key:str(value).replace(str(prior),str(out))for key,value in flow['actual_variables'].items()}
        for key,value in expected.items():
            log='variable-'+key+'.log';run(command+['print-'+key],log)
            match=re.search(r'(?m)^'+key+r': (.*)$',(out/log).read_text());assert match and match[1].strip()==value,(key,match,value)
        new['actual_variables']=expected
        run(command+['--dry-run','do-6_report'],'finish-plan.log')
        check_final_plan((out/'finish-plan.log').read_text())
        run(command+['do-6_report'],'fresh-final-report.log')
        execute('final-check','write_def final-readback.def\nwrite_verilog final-all.v\ndrt::check_drc_cmd native-router-drc.rpt 0 0 0 0 s_final_escape_drc\nwrite_def checked-readback.def\n',str(REL/'6_final.odb'))
        assert def_inventory(out/'edited.def')==def_inventory(out/'final-readback.def')
        assert sha(out/'edited.v')==sha(out/'final-all.v')
        assert sha(out/'final-readback.def')==sha(out/'checked-readback.def')
        assert sha(results/'6_final.sdc')==sha(prior/REL/'6_final.sdc')
        assert not(out/'native-router-drc.rpt').read_text().strip()
        # New final outputs, never inherited acceptance or old SPEF.
        for suffix in ['v','sdc','def','odb','spef']:
            path=results/('6_final.'+suffix);assert path.stat().st_size>0
            new['final_files'][path.name]=dict(path=str(path),sha256=sha(path),bytes=path.stat().st_size)
        from strong_driver_audit import audit as driver_audit
        new['strong_output_driver_proof']=driver_audit(results/'6_final.odb',out,788)
        proof.update(plans=plans,source=str(prior),source_receipt_sha256=sha(prior/'receipt.json'),source_files=source_files,
            edited_odb_sha256=sha(out/'edited.odb'),helper_sha256=sha(Path(__file__)),
            native_whole_drc_zero=True,regenerated_rc=True,physical_owner='block_feed_s_macro M1-M10',
            native_leaf_accepted=False,whole_system_qualified=False)
        (out/'s-escape-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
        new['S_prefreeze_escape_repair']=dict(proof_sha256=sha(out/'s-escape-proof.json'),physical_owner='block_feed_s_macro M1-M10')
        new.update(passed=True,pipeline_completed=True);(out/'native-flow.json').write_text(json.dumps(new,indent=2)+'\n')
        r['internal_drive_policy']=old['internal_drive_policy']
        r['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()};audit(out,new,r)
        r.update(passed=True,native_pipeline_completed=True)
    finally:
        r['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()}
        (out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
