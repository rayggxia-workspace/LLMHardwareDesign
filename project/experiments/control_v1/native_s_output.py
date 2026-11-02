"""User-authorized fresh S P&R with output drive owned by S, not upper metal."""
import collections,hashlib,json,os,subprocess,sys,time
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[3]


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    return h.hexdigest()


def inspect_cts(a):
    """Inspect immutable completed CTS files while final routing continues."""
    assert os.environ.get('SLURM_JOB_ID')and len(os.sched_getaffinity(0))<=16
    base=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162').resolve()
    folder=a.s_cts_folder.resolve();assert base in folder.parents
    assert folder.name=='base'and folder.parent.name=='bv1_block_feed_s_macro'
    a.out=a.out.resolve();assert base in a.out.parents;a.out.mkdir(parents=True,exist_ok=False)
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    rc=lib.parents[1]/'setRC.tcl';odb=folder/'4_cts.odb';sdc=folder/'4_cts.sdc'
    inputs={str(p):sha(p)for p in [odb,sdc,lib,rc,Path(__file__)]}
    receipt=dict(passed=False,diagnostic_only=True,native_leaf_qualified=False,whole_system_qualified=False,inputs=inputs,
        scope='Read-only completed S CTS checkpoint with placement parasitics. Reports failure locations only; no final RC/timing/physical acceptance.')
    try:
        script='set_thread_count 16\nread_liberty {'+str(lib)+'}\nread_db {'+str(odb)+'}\nread_sdc {'+str(sdc)+'}\nsource {'+str(rc)+'}\nestimate_parasitics -placement\n'
        script+='report_checks -path_delay max -group_path_count 16 -format full_clock_expanded -fields {slew cap fanout input net} -digits 6 > cts-setup.rpt\n'
        script+='report_checks -path_delay min -group_path_count 8 -format full_clock_expanded -fields {slew cap fanout input net} -digits 6 > cts-hold.rpt\n'
        script+='report_check_types -max_capacitance -max_slew -violators -digits 6 > cts-electrical.rpt\nreport_worst_slack -max\nreport_worst_slack -min\n'
        path=a.out/'inspect-cts.tcl';path.write_text(script)
        with(a.out/'inspect-cts.log').open('w')as f:q=subprocess.run(['openroad','-no_init','-exit',path],cwd=a.out,stdout=f,stderr=subprocess.STDOUT)
        receipt['returncode']=q.returncode;assert q.returncode==0
        assert all(sha(p)==digest for p,digest in inputs.items()),'CTS input changed during read-only diagnosis'
        receipt['passed']=True
    finally:
        receipt['outputs']={p.name:sha(p)for p in a.out.iterdir()if p.is_file()}
        (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')


def implement(a):
    assert os.environ.get('SLURM_JOB_ID')and len(os.sched_getaffinity(0))<=16
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    receipt=dict(passed=False,top='block_feed_s_macro',job=os.environ['SLURM_JOB_ID'],commands=[],inputs={},
        whole_system_qualified=False,native_leaf_accepted=False,
        scope='Fresh S-only M1-M10 P&R with internal output drive. Original S baseline and other five macros retained. No inherited physical/function/LEC acceptance for this new layout.')
    def read(path,digest=None):
        path=Path(path);actual=sha(path)
        if digest is not None:assert actual==digest
        receipt['inputs'][str(path)]=actual;return json.loads(path.read_text())
    def run(command,log):
        command=list(map(str,command));start=time.time()
        with (a.out/log).open('w')as f:q=subprocess.run(command,cwd=a.out,stdout=f,stderr=subprocess.STDOUT)
        receipt['commands'].append(dict(command=command,log=log,sha256=sha(a.out/log),returncode=q.returncode,seconds=time.time()-start))
        assert q.returncode==0,(log,q.returncode)
    try:
        delivery=read(a.s_native_delivery);assert delivery['passed']and delivery['native_leaf_accepted']and delivery['top']=='block_feed_s_macro'
        assert set(delivery['gate_receipts'])=={'physical','drc','function','formal'}
        source=None
        for op,row in delivery['gate_receipts'].items():
            gate=read(row['path'],row['sha256']);assert gate['passed']
            report=read(row['report_path'],row['report_sha256']);assert report['passed']
            assert report['source_receipt_sha256']==delivery['source_receipt_sha256']
            if op=='physical':source=Path(gate['source'])
        source_receipt=read(source/'receipt.json',delivery['source_receipt_sha256']);assert source_receipt['passed']
        flow=read(source/'final-source.json',source_receipt['outputs']['final-source.json'])
        assert flow['top']=='block_feed_s_macro'and flow['passed']and flow['pipeline_completed']
        for name,digest in flow['rtl_sha256'].items():assert sha(ROOT/name)==digest;receipt['inputs'][str(ROOT/name)]=digest
        for path,digest in flow['mapped_artifacts'].items():assert sha(path)==digest;receipt['inputs'][path]=digest
        mapped=next(Path(p)for p in flow['mapped_artifacts']if p.endswith('/mapped.json'))
        design=json.loads(mapped.read_text());module=design['modules']['block_feed_s_macro']
        scopes={n:c for n,c in module['cells'].items()if c['type']=='$scopeinfo'}
        assert all(not c.get('connections')for c in scopes.values()),'Scope annotation carries logic connections'
        counts=dict(collections.Counter(c['type']for c in module['cells'].values()if c['type']!='$scopeinfo'))
        assert counts and all(not c.startswith('$')for c in counts),('Unmapped logic',counts)
        receipt['portless_scope_annotations']=len(scopes)
        lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
        receipt['inputs'][str(lib)]=sha(lib)
        mapping=a.out/'mapping/block_feed_s_macro';mapping.mkdir(parents=True)
        index=dict(passed=True,mapped=True,top='block_feed_s_macro',source_sha256=flow['rtl_sha256'],liberty_sha256=sha(lib),
            cell_counts=counts,ports={n:dict(direction=p['direction'],bits=len(p['bits']))for n,p in module['ports'].items()},
            reused_artifacts=dict(scope='Exact logical mapping hashes bound by the original fully qualified S source; no original physical database reused in this fresh implementation',artifacts=flow['mapped_artifacts']),
            qualified_original_source=str(source),qualified_original_source_receipt_sha256=delivery['source_receipt_sha256'])
        (mapping/'receipt.json').write_text(json.dumps(index,indent=2)+'\n');del design,module
        for folder in ['block_v1','block_feed_v1','block_v2']:sys.path.insert(0,str(ROOT/'project/experiments'/folder))
        import physical
        args=SimpleNamespace(out=a.out,top='block_feed_s_macro',mapping=a.out/'mapping',input_receivers=True,
            remove_abc_buffers=True,placement_mode='geometric',fanout_mode='partition',placement_density=a.placement_density,
            control_escape_repair=[],r_compact_floorplan=False,r_strong_clock=False,refine_partition_placement=False,
            strong_output_drivers=True,placement_hold_margin=None,hold_repair_margin=a.s_hold_margin)
        receipt['internal_drive_policy']=dict(master='BUF_X32',output_bits=sum(p['bits']for p in index['ports'].values()if p['direction']=='output'),
            no_new_registers=True,no_latency_or_protocol_change=True,physical_owner='block_feed_s_macro M1-M10')
        physical.implement(args,run);receipt.update(passed=True,native_pipeline_completed=True)
    finally:
        receipt['outputs']={str(p.relative_to(a.out)):sha(p)for p in a.out.rglob('*')if p.is_file()}
        (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
