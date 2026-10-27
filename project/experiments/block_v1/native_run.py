"""Run native M1-M10 candidates; physical qualification is a separate receiver.

Read the exact mapped structural view directly. No RTL resynthesis, custom
metal, extra SRAM, relaxed constraints or disabled default checks are added.
"""
import hashlib
import json
from pathlib import Path
import re
import shutil
from io_slots import slot


def sha(path):
    digest=hashlib.sha256()
    with path.open('rb')as stream:
        for data in iter(lambda:stream.read(1024*1024),b''):digest.update(data)
    return digest.hexdigest()


def implement(root,out,cpus,run,top,policy,pipeline='native_pipeline.json'):
    assert top in ('shared109','transaction6k')and policy in('A','C')and cpus>=16
    assert pipeline in ('native_pipeline.json','native_pipeline_const.json')
    config=json.loads((root/'project/experiments/block_v1'/pipeline).read_text())
    base=out.parents[2];audit=base/config['boundary_audit_run']/'tasks/native-boundary-audit'
    prior=json.loads((audit/'receipt.json').read_text());assert prior['passed']is True
    path=audit/'native-boundary-audit.json';assert sha(path)==prior['outputs'][path.name]
    accepted=json.loads(path.read_text());assert accepted['passed']is True
    candidate=next(c for c in accepted['candidates']if c['top']==top and c['policy']==policy)
    assert sha(Path(candidate['source'])/'receipt.json')==candidate['receipt_sha256']
    prep=base/config['preparation_run']/'tasks/native-prepare'
    bound=json.loads((prep/'receipt.json').read_text());assert bound['passed']is True
    folder=prep/(top+'-'+policy);inputs=prep/'inputs'/top
    for path in [folder/'config.mk',folder/'pins.tcl',inputs/(top+'.v'),inputs/(top+'.sdc')]:
        assert sha(path)==bound['outputs'][str(path.relative_to(prep))]
    nickname='bv1_'+top+'_'+policy
    results=out/'flow/results/nangate45'/nickname/'base';results.mkdir(parents=True)
    # do-1_synth imports these mapped files through OpenROAD synth_odb.tcl;
    # it does not invoke Yosys. Independent read-only copies prevent any
    # unexpected downstream write from reaching the frozen source files.
    copied={}
    with slot(base):
        for suffix in ['v','sdc']:
            path=results/('1_2_yosys.'+suffix)
            shutil.copyfile(inputs/(top+'.'+suffix),path)
            path.chmod(0o444);copied[path]=sha(path)
    command=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(folder/'config.mk'),
             'WORK_HOME='+str(out/'flow'),'NUM_CORES='+str(cpus)]
    record=dict(schema='block-v1-native-candidate/1',top=top,policy=policy,cpus=cpus,
        inputs_source=str(prep),inputs_receipt_sha256=sha(prep/'receipt.json'),
        boundary_audit_sha256=sha(audit/'native-boundary-audit.json'),stages=[],
        qualified_hard_macro=False,
        scope='Native ten-layer candidate P&R; twelve-layer distributed extraction and all complete physical acceptance gates remain required')
    def save():(out/'native-candidate.json').write_text(json.dumps(record,indent=2)+'\n')
    save()
    for variable in ['TECH_LEF','MAX_ROUTING_LAYER','MIN_ROUTING_LAYER','RCX_RULES','KEEP_VARS','LEC_CHECK','SEC_CHECK']:
        run(command+['print-'+variable],'variable-'+variable+'.log')
    def value(name):
        return re.search(r'(?m)^'+name+r': (.+)$',(out/('variable-'+name+'.log')).read_text()).group(1).strip()
    assert value('MAX_ROUTING_LAYER')=='metal10' and value('MIN_ROUTING_LAYER')=='metal1'
    assert value('TECH_LEF')=='/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef'
    assert value('RCX_RULES')=='/OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules'
    assert value('KEEP_VARS')=='1'
    record['actual_variables']={name:value(name)for name in ['TECH_LEF','MIN_ROUTING_LAYER','MAX_ROUTING_LAYER','RCX_RULES','KEEP_VARS','LEC_CHECK','SEC_CHECK']}
    for index,stage in enumerate(['do-1_synth','do-floorplan','do-place','do-cts','do-route','do-finish']):
        run(command+[stage],'%02d-%s.log'%(index,stage))
        with slot(base):
            assert all(sha(path)==digest for path,digest in copied.items()),'Mapped inputs unexpectedly changed'
        record['stages'].append(stage);save()
    record['pipeline_completed']=True
    record['final_files']={path.name:dict(path=str(path),sha256=sha(path))for path in results.glob('6_final.*')if path.is_file()}
    assert all('6_final.'+suffix in record['final_files']for suffix in ['odb','sdc','v','spef'])
    save()
