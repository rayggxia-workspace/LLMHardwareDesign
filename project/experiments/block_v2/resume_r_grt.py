"""Resume completed R GRT with measured optimization margins, then native route/final.

Only successful, digest-bound checkpoints are inherited from a failed producer.
No failed final stage or earlier physical qualification is transferred.
"""
import argparse
import copy
import json
from pathlib import Path
import re
import shutil
import subprocess
import time

from physical import sha,ROOT


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--input-hold-guard',action='store_true',help='Use conservative input-only arrival guard during optimization; restore real SDC')
    p.add_argument('--guard-reset',action='store_true',help='Also guard reset after measured final reset hold failures')
    a=p.parse_args();a.source=a.source.resolve();a.out=a.out.resolve()
    assert a.source!=a.out and 'issue143-seven-block-v2-20261030' in a.out.parts
    r=json.loads((a.source/'receipt.json').read_text());assert r['passed'] is False
    original=a.source/'native-flow.json';assert sha(original)==r['outputs'][original.name]
    old=json.loads(original.read_text());assert old['top']=='block_v1_r' and old['passed'] is False
    stages=['do-1_synth','do-floorplan','do-place','do-cts','do-route']
    assert old['stages']==stages
    assert not a.guard_reset or a.input_hold_guard
    # A resumed producer retains the original successful first four stages.
    # Its own successful route supplies the newer GRT, with a separate binding.
    origin=a.source
    origin_receipt=r
    if old.get('inherited_physical_stages'):
        assert old['inherited_physical_stages']==stages[:4]
        origin=Path(old['source_native_folder']).resolve()
        origin_receipt=json.loads((origin/'receipt.json').read_text())
        assert sha(origin/'receipt.json')==r['inputs'][str(origin/'receipt.json')]
        assert sha(origin/'native-flow.json')==old['source_native_journal_sha256']==origin_receipt['outputs']['native-flow.json']
        for name,row in old['source_cts_files'].items():
            assert sha(row['path'])==row['sha256']==origin_receipt['outputs'][str(Path(row['path']).relative_to(origin))]
    for path,digest in old['rtl_sha256'].items():assert sha(ROOT/path)==digest
    for i,stage in enumerate(stages):
        producer=origin_receipt if i<4 else r
        directory=origin if i<4 else a.source
        name='%02d-%s.log'%(i,stage);assert sha(directory/name)==producer['outputs'][name]
        if i<4 and origin!=a.source:assert sha(directory/name)==old['source_cts_stage_log_sha256'][name]
        commands=[c for c in producer['commands'] if c['log']==name]
        assert len(commands)==1 and commands[0]['returncode']==0
    a.out.mkdir(parents=True,exist_ok=False)
    receipt=dict(passed=False,top=old['top'],commands=[],inputs={str(a.source/'receipt.json'):sha(a.source/'receipt.json')})
    receipt['inputs'][str(origin/'receipt.json')]=sha(origin/'receipt.json')
    for directory in ('project/experiments/block_v2','project/experiments/block_v1','project/experiments/block_feed_v1'):
        for file in (ROOT/directory).rglob('*'):
            if file.is_file() and '__pycache__' not in file.parts:receipt['inputs'][str(file.relative_to(ROOT))]=sha(file)
    relative=Path('flow/results/nangate45/bv1_block_v1_r/base');before=a.source/relative;after=a.out/relative
    after.mkdir(parents=True)
    def checked_copy(source,target):
        assert sha(source)==r['outputs'][str(source.relative_to(a.source))]
        shutil.copyfile(source,target);assert sha(target)==sha(source)
    flow=copy.deepcopy(old);flow.update(passed=False,pipeline_completed=False,final_files={},
        inherited_physical_stages=stages[:4],stages=stages[:4],source_native_folder=str(origin),
        source_native_journal_sha256=sha(origin/'native-flow.json'),source_cts_stage_log_sha256={},source_cts_files={},
        qualified_hard_macro=False)
    for i,stage in enumerate(stages[:4]):
        name='%02d-%s.log'%(i,stage);flow['source_cts_stage_log_sha256'][name]=sha(origin/name)
    for name in ('4_cts.odb','4_cts.sdc'):
        src=origin/relative/name;assert sha(src)==origin_receipt['outputs'][str(src.relative_to(origin))]
        flow['source_cts_files'][name]=dict(path=str(src),sha256=sha(src))
    checkpoint={}
    for name in ('5_1_grt.odb','5_1_grt.sdc'):
        src=before/name;assert sha(src)==r['outputs'][str(src.relative_to(a.source))]
        checkpoint[name]=dict(path=str(src),sha256=sha(src))
    flow['source_grt_checkpoint']=dict(folder=str(a.source),receipt_sha256=sha(a.source/'receipt.json'),
        files=checkpoint,journal_name='native-flow.json',journal_sha256=sha(original))
    try:
        for name in ('pins.json','pins.tcl','input.sdc','input.v','input-diodes.tcl'):
            checked_copy(a.source/name,a.out/name)
        checked_copy(a.source/'config.mk',a.out/'original-config.mk')
        config=(a.out/'original-config.mk').read_text().replace(str(a.source),str(a.out))
        assert str(a.source) not in config
        config+='\n# Measured final RC deficits: setup164ps / hold109ps. Optimization only; no SDC exception.\n'
        hold_margin='0.020' if a.input_hold_guard else '0.150'
        config+='export SETUP_SLACK_MARGIN = 0.200\nexport HOLD_SLACK_MARGIN = '+hold_margin+'\n'
        # Receivers and diodes already exist in the inherited GRT. Never add twice.
        pre_global=''
        if a.input_hold_guard:
            src=ROOT/'project/experiments/block_v2'/('r_input_hold_reset_guard.tcl' if a.guard_reset else 'r_input_hold_guard.tcl')
            target=a.out/'r-input-hold-guard.tcl';shutil.copyfile(src,target);assert sha(src)==sha(target)
            pre_global=str(target)
            flow['input_hold_guard']=dict(script_sha256=sha(target),ports='cmd_data[127:0],reset' if a.guard_reset else 'cmd_data[127:0]',
                optimization_input_min_ns=0.0,actual_input_min_ns=.2,global_hold_margin_ns=.020,
                basis='084 exact final RC: setup+7.728485ps, cap/slew0, hold30 worst-46.371240ps on reset. Include reset in200ps earlier optimization-only arrival guard; restore actual SDC.' if a.guard_reset else '076 globalhold.15 targets146338 endpoints; original real routed hold failures are input paths. Use200ps earlier input during optimization only, and restore actual contract before final SDC.')
        config+='export PRE_GLOBAL_ROUTE_TCL = '+pre_global+'\n'
        (a.out/'config.mk').write_text(config)
        for name in ('1_synth_lec.v','1_2_yosys.v','1_2_yosys.sdc','bv1-input-diodes.tsv','feed-input-receivers.tsv'):
            checked_copy(before/name,after/name)
        checked_copy(before/'5_1_grt.odb',after/'4_cts.odb')
        checked_copy(before/'5_1_grt.sdc',after/'4_cts.sdc')
        flow.update(config_sha256=sha(a.out/'config.mk'),pins_sha256=sha(a.out/'pins.json'),
            hold_repair_margin_ns=float(hold_margin),setup_repair_margin_ns=.200,
            resume_scope='Original completed GRT used as native route input, with existing CTS/receivers/diodes; repeat full native GRT repair and detailed route/final. No final success inherited.')
        command=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(a.out/'config.mk'),'WORK_HOME='+str(a.out/'flow'),'NUM_CORES=16']
        def run(cmd,log):
            started=time.time()
            with (a.out/log).open('w') as stream:
                result=subprocess.run(list(map(str,cmd)),cwd=a.out,stdout=stream,stderr=subprocess.STDOUT)
            receipt['commands'].append(dict(command=list(map(str,cmd)),log=log,sha256=sha(a.out/log),returncode=result.returncode,seconds=time.time()-started))
            assert result.returncode==0,(log,result.returncode)
        wanted=dict(LEC_CHECK='1',SEC_CHECK='0',SETUP_SLACK_MARGIN='0.200',HOLD_SLACK_MARGIN=hold_margin,
            MIN_ROUTING_LAYER='metal1',MAX_ROUTING_LAYER='metal10',PRE_GLOBAL_ROUTE_TCL=pre_global)
        for key,value in wanted.items():
            log='variable-'+key+'.log';run(command+['print-'+key],log)
            matches=re.findall(r'(?m)^'+key+r':(.*)$',(a.out/log).read_text());assert len(matches)==1
            assert matches[0].strip()==value,(key,matches,value)
            flow['actual_variables'][key]=value
        def save():(a.out/'native-flow.json').write_text(json.dumps(flow,indent=2)+'\n')
        save()
        for number,stage in ((4,'do-route'),(5,'do-finish')):
            run(command+[stage],'%02d-%s.log'%(number,stage));flow['stages'].append(stage);save()
        for suffix in ('v','sdc','def','odb','spef'):
            file=after/('6_final.'+suffix);assert file.is_file()
            flow['final_files'][file.name]=dict(path=str(file),sha256=sha(file),bytes=file.stat().st_size)
        flow.update(passed=True,pipeline_completed=True);save();receipt['passed']=True
    finally:
        receipt['outputs']={str(file.relative_to(a.out)):sha(file) for file in a.out.rglob('*') if file.is_file()}
        (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':main()
