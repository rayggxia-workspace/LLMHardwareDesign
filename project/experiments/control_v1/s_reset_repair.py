"""Source-bound S-only data-delay ECO; every final qualification is rerun."""
import copy,hashlib,json,os,re,shutil,subprocess,time
from pathlib import Path
from s_reset_branch import slacks
from native_s_output import sha
ROOT=Path(__file__).resolve().parents[3]
REL=Path('flow/results/nangate45/bv1_block_feed_s_macro/base')


def config(payload,count):
    assert count in (96,128)
    evidence=json.loads(payload)
    assert evidence['passed']and evidence['diagnostic_only']and evidence['no_database_or_constraint_mutation']
    assert evidence['rc_model']=='placement-estimate-on-completed-post-GRT-ODB'
    rows=[r for r in evidence['branches']if r['has_timed_reset_path']and r['minimum_hold_ns']<-.1]
    assert len(rows)==5 and len({r['instance']for r in rows})==5
    for r in rows:
        assert re.fullmatch(r'\$abc\$\d+\$auto\$blifparse\.cc:397:parse_blif\$\d+',r['instance'])
        assert r['pin']=='A'and r['master']=='AOI21_X1'and r['net']=='net175'
        assert -.7<r['minimum_hold_ns']<-.1 and r['minimum_setup_ns']>2.0
    text='set s_reset_count '+str(count)+'\nset s_reset_evidence_sha '+hashlib.sha256(payload).hexdigest()+'\nset s_reset_targets {\n'
    text+='\n'.join(' {'+' '.join(r[k]for k in ['instance','pin','master','net'])+'}'for r in rows)+'\n}\n'
    return text,rows


def audit(raw,flow,receipt,file_sha=sha):
    proof=flow['S_reset_branch_repair'];payload=(raw/'s-reset-evidence.json').read_bytes()
    for kind in ['odb','sdc']:
        checkpoint=flow['source_grt_checkpoint']['files']['5_1_grt.'+kind]
        assert file_sha(raw/REL/('4_cts.'+kind))==checkpoint['sha256']
    expected,targets=config(payload,proof['buffers_per_branch'])
    assert(raw/'s-reset-config.tcl').read_text()==expected
    assert file_sha(raw/'s-reset-evidence.json')==proof['evidence_sha256']==receipt['outputs']['s-reset-evidence.json']
    assert file_sha(raw/'s-reset-delay.tcl')==proof['script_sha256']==receipt['outputs']['s-reset-delay.tcl']
    assert file_sha(Path(__file__))==proof['auditor_sha256']
    table=raw/REL/'s-reset-delay.tsv';assert file_sha(table)==proof['table_sha256']==receipt['outputs'][str(table.relative_to(raw))]
    rows=[line.split('\t')for line in table.read_text().splitlines()]
    assert rows[0]==['config',str(proof['buffers_per_branch']),proof['evidence_sha256']]
    added=[r for r in rows if r[0]=='buffer'];verified=[r for r in rows if r[0]=='verified']
    assert len(added)==5*proof['buffers_per_branch']and len(verified)==5
    for number,target in enumerate(targets):
        selected=[r for r in rows if r[0]=='target'and int(r[1])==number]
        assert len(selected)==1 and selected[0][2:5]==[target['instance'],'A','net175']and float(selected[0][5])>=2.0
        chain=[r for r in added if int(r[1])==number]
        for index,row in enumerate(chain):
            name='issue162_s_reset_'+str(number)+'_'+str(index)
            previous='net175'if index==0 else 'issue162_s_reset_'+str(number)+'_'+str(index-1)+'_net'
            assert row==['buffer',str(number),str(index),name,'BUF_X1',previous,name+'_net']
        assert verified[number]==['verified',str(number),'other_inputs_output_PG_and_fanout_preserved']
        for kind in ['min','max']:
            p=raw/REL/('s-reset-after-'+str(number)+'-'+kind+'.rpt')
            assert file_sha(p)==receipt['outputs'][str(p.relative_to(raw))]
            values=slacks(p);assert values and min(values)>=0
    before=list(map(int,(raw/REL/'s-reset-before-counts.tsv').read_text().split()))
    after=list(map(int,(raw/REL/'s-reset-after-counts.tsv').read_text().split()))
    assert len(before)==len(after)==4 and all(after[i]<=before[i]for i in range(3))
    final=raw/'s-reset-final.tsv';assert file_sha(final)==proof['final_table_sha256']==receipt['outputs'][final.name]
    final_rows=[r.split('\t')for r in final.read_text().splitlines()]
    assert len(final_rows)==5*proof['buffers_per_branch']
    assert final_rows==[[r[3],r[4],r[5],r[6]]for r in added]
    assert proof['no_new_registers']and proof['physical_owner']=='block_feed_s_macro M1-M10'


def implement(a):
    assert os.environ.get('SLURM_JOB_ID')and len(os.sched_getaffinity(0))<=16
    base=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162').resolve()
    prior=a.s_native_source.resolve();out=a.out.resolve()
    assert base in prior.parents and base in out.parents
    out.mkdir(parents=True,exist_ok=False)
    receipt=dict(passed=False,top='block_feed_s_macro',job=os.environ['SLURM_JOB_ID'],commands=[],inputs={},
        native_leaf_accepted=False,whole_system_qualified=False,
        scope='Reuse exact completed S placement/CTS/GRT optimization; add measured reset-only combinational delay, reroute/finish and rerun all final gates. No source acceptance or failed hold result inherited.')
    def bind(path,digest=None):
        actual=sha(path)
        if digest is not None:assert actual==digest
        receipt['inputs'][str(path)]=actual;return actual
    def run(command,log):
        command=list(map(str,command));start=time.time()
        with(out/log).open('w')as stream:q=subprocess.run(command,cwd=out,stdout=stream,stderr=subprocess.STDOUT)
        receipt['commands'].append(dict(command=command,log=log,returncode=q.returncode,seconds=time.time()-start,sha256=sha(out/log)))
        assert q.returncode==0,(log,q.returncode)
    try:
        old=json.loads((prior/'receipt.json').read_text());assert old['top']=='block_feed_s_macro'
        bind(prior/'receipt.json');flow=json.loads((prior/'native-flow.json').read_text());bind(prior/'native-flow.json',old['outputs']['native-flow.json'])
        stages=['do-1_synth','do-floorplan','do-place','do-cts']
        assert flow['top']=='block_feed_s_macro'and flow['stages'][:4]==stages
        assert old['internal_drive_policy']['physical_owner']=='block_feed_s_macro M1-M10'
        assert old['internal_drive_policy']['output_bits']==788 and flow['strong_output_drivers']
        for index,stage in enumerate(stages):
            name='%02d-%s.log'%(index,stage)
            entries=[c for c in old['commands']if c['log']==name]
            assert len(entries)==1 and entries[0]['returncode']==0
            bind(prior/name,entries[0]['sha256']);assert entries[0]['sha256']==old['outputs'][name]
        receipt['source_pipeline_passed']=old['passed']
        receipt['source_reuse_scope']='Only completed placement/CTS/GRT checkpoints; no route/final, hold or native acceptance inherited, including when the retained source later failed.'
        assert not flow.get('S_reset_branch_repair')
        for name,digest in flow['rtl_sha256'].items():bind(ROOT/name,digest)
        for name,digest in old['inputs'].items():bind(name,digest)
        evidence=a.s_reset_evidence.resolve();e=json.loads((evidence/'receipt.json').read_text());assert e['passed']and e['diagnostic_only']
        bind(evidence/'receipt.json');payload=(evidence/'reset-branch-measurements.json').read_bytes()
        bind(evidence/'reset-branch-measurements.json',e['outputs']['reset-branch-measurements.json'])
        for name,digest in e['inputs'].items():bind(name,digest)
        assert e['inputs'][str(prior/REL/'5_1_grt.odb')]==sha(prior/REL/'5_1_grt.odb')
        text,targets=config(payload,a.s_reset_buffers)
        (out/'s-reset-evidence.json').write_bytes(payload);(out/'s-reset-config.tcl').write_text(text)
        helper=Path(__file__).with_name('s_reset_delay.tcl');bind(helper)
        for path in prior.iterdir():
            if path.is_file()and(path.name in ['input.v','input.sdc','pins.json','config.mk']or path.suffix in ['.lef','.tcl']):
                bind(path,old['outputs'][path.name]);shutil.copyfile(path,out/path.name)
        # Restore generated ECO files after copying the original top-level inputs.
        (out/'s-reset-evidence.json').write_bytes(payload);(out/'s-reset-config.tcl').write_text(text)
        shutil.copyfile(helper,out/'s-reset-delay.tcl')
        results=out/REL;results.mkdir(parents=True)
        copies=[('4_cts.odb','5_1_grt.odb'),('4_cts.sdc','5_1_grt.sdc')]
        copies +=[(name,name)for name in ['1_2_yosys.v','1_2_yosys.sdc','1_synth_lec.v','bv1-input-diodes.tsv','strong-output-drivers.tsv','feed-input-receivers.tsv','feed-partition-fanout.tsv']]
        for dest,source in copies:
            path=prior/REL/source;bind(path,old['outputs'][str(path.relative_to(prior))]);shutil.copyfile(path,results/dest)
        mk=(prior/'config.mk').read_text().replace(str(prior),str(out))
        removed={'PRE_GLOBAL_ROUTE_TCL','POST_GLOBAL_ROUTE_TCL','SKIP_INCREMENTAL_REPAIR','OPT_POST_GRT_WNS'}
        mk='\n'.join(line for line in mk.splitlines()if not any(re.match(r'\s*(?:export\s+)?'+name+r'\s*[:?+]?=',line)for name in removed))+'\n'
        mk+='export PRE_GLOBAL_ROUTE_TCL =\nexport POST_GLOBAL_ROUTE_TCL = '+str(out/'s-reset-delay.tcl')+'\nexport SKIP_INCREMENTAL_REPAIR = 1\nexport OPT_POST_GRT_WNS = 1\n'
        (out/'config.mk').write_text(mk)
        new=copy.deepcopy(flow);new.update(passed=False,pipeline_completed=False,stages=flow['stages'][:4],final_files={},
            inherited_physical_stages=flow['stages'][:4],source_native_folder=str(prior),
            source_native_journal_sha256=sha(prior/'native-flow.json'),config_sha256=sha(out/'config.mk'))
        new['source_cts_stage_log_sha256']={('%02d-%s.log'%(i,stage)):bind(prior/('%02d-%s.log'%(i,stage)),old['outputs']['%02d-%s.log'%(i,stage)])for i,stage in enumerate(flow['stages'][:4])}
        new['source_cts_files']={name:dict(path=str(prior/REL/name),sha256=bind(prior/REL/name,old['outputs'][str(REL/name)]))for name in ['4_cts.odb','4_cts.sdc']}
        new['source_grt_checkpoint']=dict(folder=str(prior),receipt_sha256=sha(prior/'receipt.json'),journal_name='native-flow.json',journal_sha256=sha(prior/'native-flow.json'),
            files={name:dict(path=str(prior/REL/name),sha256=bind(prior/REL/name,old['outputs'][str(REL/name)]))for name in ['5_1_grt.odb','5_1_grt.sdc']})
        command=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(out/'config.mk'),'WORK_HOME='+str(out/'flow'),'NUM_CORES=16',
            '--assume-old='+str(results/'4_cts.odb'),'--assume-old='+str(results/'4_cts.sdc')]
        expected={key:str(value).replace(str(prior),str(out))for key,value in flow['actual_variables'].items()}
        expected.update(SKIP_INCREMENTAL_REPAIR='1',OPT_POST_GRT_WNS='1',POST_GLOBAL_ROUTE_TCL=str(out/'s-reset-delay.tcl'),PRE_GLOBAL_ROUTE_TCL='')
        for key,value in expected.items():
            log='variable-'+key+'.log';run(command+['print-'+key],log)
            actual=re.search(r'(?m)^'+key+r': (.*)$',(out/log).read_text()).group(1).strip();assert actual==value,(key,actual,value)
            new['actual_variables'][key]=actual
        def save():(out/'native-flow.json').write_text(json.dumps(new,indent=2)+'\n')
        save()
        run(command+['--dry-run','do-route'],'reuse-plan.log')
        plan=(out/'reuse-plan.log').read_text()
        assert 'global_route.tcl'in plan
        assert not any(token in plan for token in ['synth.sh','global_place.tcl','floorplan.tcl','cts.tcl']),'Refuse unintended predecessor rebuild'
        for index,stage in [(4,'do-route'),(5,'do-finish')]:
            run(command+[stage],'%02d-%s.log'%(index,stage));new['stages'].append(stage);save()
        for suffix in ['v','sdc','def','odb','spef']:
            path=results/('6_final.'+suffix);assert path.is_file()
            new['final_files'][path.name]=dict(path=str(path),sha256=sha(path),bytes=path.stat().st_size)
        from strong_driver_audit import audit as output_audit
        new['strong_output_driver_proof']=output_audit(results/'6_final.odb',out,788)
        script='set_thread_count 16\nread_db {'+str(results/'6_final.odb')+'}\nset f [open {'+str(out/'s-reset-final.tsv')+'} w]\n'
        for number,target in enumerate(targets):
            for index in range(a.s_reset_buffers):
                name='issue162_s_reset_'+str(number)+'_'+str(index)
                previous='net175'if index==0 else'issue162_s_reset_'+str(number)+'_'+str(index-1)+'_net'
                script+='set inst [[ord::get_db_block] findInst '+name+']\nif {$inst eq "NULL" || [[$inst getMaster] getName] ne "BUF_X1"} {error "Final S reset delay missing"}\n'
                script+='set a [[$inst findITerm A] getNet];set z [[$inst findITerm Z] getNet]\n'
                script+='if {$a eq "NULL" || $z eq "NULL" || [$a getName] ne "'+previous+'" || [$z getName] ne "'+name+'_net"} {error "Final S delay chain disconnected"}\n'
                script+='puts $f "[$inst getName]\\t[[$inst getMaster] getName]\\t[$a getName]\\t[$z getName]"\n'
            script+='set target [[ord::get_db_block] findInst {'+target['instance']+'}]\nif {$target eq "NULL" || [[[$target findITerm A] getNet] getName] ne "issue162_s_reset_'+str(number)+'_'+str(a.s_reset_buffers-1)+'_net"} {error "Final S branch target disconnected"}\n'
        script+='close $f\n';(out/'s-reset-final.tcl').write_text(script)
        before=sha(results/'6_final.odb');run(['openroad','-no_init','-exit',out/'s-reset-final.tcl'],'s-reset-final.log');assert before==sha(results/'6_final.odb')
        new['S_reset_branch_repair']=dict(buffers_per_branch=a.s_reset_buffers,evidence_sha256=sha(out/'s-reset-evidence.json'),script_sha256=sha(out/'s-reset-delay.tcl'),auditor_sha256=sha(Path(__file__)),
            table_sha256=sha(results/'s-reset-delay.tsv'),final_table_sha256=sha(out/'s-reset-final.tsv'),physical_owner='block_feed_s_macro M1-M10',no_new_registers=True,
            source_diagnostic=str(evidence),source_diagnostic_receipt_sha256=sha(evidence/'receipt.json'))
        receipt['internal_drive_policy']=old['internal_drive_policy'];new.update(passed=True,pipeline_completed=True);save()
        receipt['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()}
        audit(out,new,receipt)
        receipt.update(passed=True,native_pipeline_completed=True)
    finally:
        receipt['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()}
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
