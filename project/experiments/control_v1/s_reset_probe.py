"""Read-only-source S ECO probe through GRT, independent of pending final LEC.

This cannot qualify a leaf. The full source-bound route/final producer and every
native/PG/combination gate are still required after its original receipt closes.
"""
import json,os,re,shutil,subprocess,time
from pathlib import Path
from s_reset_repair import config,REL
from native_s_output import sha


def inspect(a):
    assert os.environ.get('SLURM_JOB_ID')and len(os.sched_getaffinity(0))<=16
    base=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162').resolve()
    prior=a.s_native_source.resolve();evidence=a.s_reset_evidence.resolve();out=a.out.resolve()
    assert all(base in p.parents for p in [prior,evidence,out])
    out.mkdir(parents=True,exist_ok=False)
    receipt=dict(passed=False,diagnostic_only=True,native_leaf_qualified=False,whole_system_qualified=False,
        inputs={},commands=[],job=os.environ['SLURM_JOB_ID'],scope='Independent completed-GRT ECO probe only. Pending source final LEC/receipt not consumed or accepted; all full qualification remains mandatory.')
    def bind(path,digest=None):
        actual=sha(path)
        if digest is not None:assert actual==digest
        receipt['inputs'][str(path)]=actual;return actual
    def run(command,log):
        start=time.time();command=list(map(str,command))
        with(out/log).open('w')as stream:q=subprocess.run(command,cwd=out,stdout=stream,stderr=subprocess.STDOUT)
        receipt['commands'].append(dict(command=command,log=log,returncode=q.returncode,seconds=time.time()-start,sha256=sha(out/log)))
        assert q.returncode==0,(log,q.returncode)
    try:
        e=json.loads((evidence/'receipt.json').read_text());assert e['passed']and e['diagnostic_only']
        bind(evidence/'receipt.json')
        for name,digest in e['inputs'].items():bind(name,digest)
        payload=(evidence/'reset-branch-measurements.json').read_bytes();bind(evidence/'reset-branch-measurements.json',e['outputs']['reset-branch-measurements.json'])
        text,targets=config(payload,a.s_reset_buffers)
        assert e['inputs'][str(prior/REL/'5_1_grt.odb')]==sha(prior/REL/'5_1_grt.odb')
        assert e['inputs'][str(prior/REL/'5_1_grt.sdc')]==sha(prior/REL/'5_1_grt.sdc')
        # Only a captured diagnostic journal, never a producer success receipt.
        snapshot=(prior/'native-flow.json').read_bytes();(out/'source-journal-captured.json').write_bytes(snapshot)
        flow=json.loads(snapshot);assert flow['top']=='block_feed_s_macro'
        assert flow['stages'][:4]==['do-1_synth','do-floorplan','do-place','do-cts']
        assert sha(prior/'config.mk')==flow['config_sha256']and sha(prior/'pins.json')==flow['pins_sha256']
        for path in prior.iterdir():
            if path.is_file()and(path.name in ['input.v','input.sdc','pins.json','config.mk']or path.suffix in ['.lef','.tcl']):
                bind(path);shutil.copyfile(path,out/path.name)
        (out/'s-reset-evidence.json').write_bytes(payload);(out/'s-reset-config.tcl').write_text(text)
        helper=Path(__file__).with_name('s_reset_delay.tcl');bind(helper);shutil.copyfile(helper,out/'s-reset-delay.tcl')
        results=out/REL;results.mkdir(parents=True)
        for dest,source in [('4_cts.odb','5_1_grt.odb'),('4_cts.sdc','5_1_grt.sdc')]:
            bind(prior/REL/source);shutil.copyfile(prior/REL/source,results/dest)
        mk=(out/'config.mk').read_text().replace(str(prior),str(out))
        removed={'PRE_GLOBAL_ROUTE_TCL','POST_GLOBAL_ROUTE_TCL','SKIP_INCREMENTAL_REPAIR','OPT_POST_GRT_WNS'}
        mk='\n'.join(line for line in mk.splitlines()if not any(re.match(r'\s*(?:export\s+)?'+name+r'\s*[:?+]?=',line)for name in removed))+'\n'
        mk+='export PRE_GLOBAL_ROUTE_TCL =\nexport POST_GLOBAL_ROUTE_TCL = '+str(out/'s-reset-delay.tcl')+'\nexport SKIP_INCREMENTAL_REPAIR = 1\nexport OPT_POST_GRT_WNS = 1\n'
        (out/'config.mk').write_text(mk)
        command=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(out/'config.mk'),'WORK_HOME='+str(out/'flow'),'NUM_CORES=16',
            '--assume-old='+str(results/'4_cts.odb'),'--assume-old='+str(results/'4_cts.sdc')]
        expected={key:str(value).replace(str(prior),str(out))for key,value in flow['actual_variables'].items()}
        expected.update(SKIP_INCREMENTAL_REPAIR='1',OPT_POST_GRT_WNS='1',POST_GLOBAL_ROUTE_TCL=str(out/'s-reset-delay.tcl'),PRE_GLOBAL_ROUTE_TCL='')
        for key,value in expected.items():
            log='variable-'+key+'.log';run(command+['print-'+key],log)
            actual=re.search(r'(?m)^'+key+r': (.*)$',(out/log).read_text()).group(1).strip();assert actual==value,(key,actual,value)
        run(command+['--dry-run',results/'5_1_grt.odb'],'probe-plan.log')
        plan=(out/'probe-plan.log').read_text()
        assert 'global_route.tcl'in plan
        assert not any(token in plan for token in ['synth.sh','global_place.tcl','floorplan.tcl','cts.tcl']),'Refuse unintended predecessor rebuild'
        run(command+[results/'5_1_grt.odb'],'probe-grt.log')
        assert(results/'s-reset-delay.tsv').is_file()and(results/'5_1_grt.odb').is_file()
        rows=[line.split('\t')for line in(results/'s-reset-delay.tsv').read_text().splitlines()]
        assert len([r for r in rows if r[0]=='buffer'])==5*a.s_reset_buffers
        assert len([r for r in rows if r[0]=='verified'])==5
        from s_reset_branch import slacks
        for number in range(5):
            for kind in ['min','max']:
                values=slacks(results/('s-reset-after-'+str(number)+'-'+kind+'.rpt'));assert values and min(values)>=0
        assert all(sha(name)==digest for name,digest in receipt['inputs'].items()),'Read-only completed source changed during probe'
        receipt.update(passed=True,physical_owner='block_feed_s_macro M1-M10',no_new_registers=True,buffers_per_branch=a.s_reset_buffers)
    finally:
        receipt['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()}
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
