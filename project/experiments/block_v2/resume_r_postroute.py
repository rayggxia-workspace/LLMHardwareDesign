"""Finish a measured single-buffer copy of failed123; inherit no final success.

The completed original five stages, candidate's exact geometry/pin contacts and
native whole DRC are independently hash-bound. Full native finish/LEC, fresh RC
and every original independent acceptance gate remain mandatory.
"""
import argparse
import copy
import json
from pathlib import Path
import re
import shutil
import subprocess
import time
from physical import ROOT, sha
from postroute_buffer_audit import compare_def_lines, pin_contact_audit


def main():
    parser=argparse.ArgumentParser()
    for name in ('source','candidate','out'):parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args()
    a.source=a.source.resolve();a.candidate=a.candidate.resolve();a.out=a.out.resolve()
    assert a.source.parts[-3:]==('123','pnr','r') and a.candidate.name=='129'
    assert 'issue143-seven-block-v2-20261030' in a.out.parts and a.out not in (a.source,a.candidate)
    old_receipt=json.loads((a.source/'receipt.json').read_text());assert old_receipt['passed'] is False
    assert sha(a.source/'receipt.json')==sha(ROOT/'work/YUZE-LU/143/r-input-hold/final-126/receipt.json')
    assert sha(a.source/'native-flow.json')==old_receipt['outputs']['native-flow.json']
    old=json.loads((a.source/'native-flow.json').read_text())
    stages=['do-1_synth','do-floorplan','do-place','do-cts','do-route']
    assert old['top']=='block_v1_r' and old['stages']==stages and old['passed'] is False
    for path,digest in old['rtl_sha256'].items():assert sha(ROOT/path)==digest
    original=Path(old['source_native_folder'])
    origin_receipt=json.loads((original/'receipt.json').read_text())
    stage_logs={}
    for i,stage in enumerate(stages):
        source=original if i<4 else a.source
        receipt=origin_receipt if i<4 else old_receipt
        name='%02d-%s.log'%(i,stage)
        assert sha(source/name)==receipt['outputs'][name]
        commands=[c for c in receipt['commands'] if c['log']==name]
        assert len(commands)==1 and commands[0]['returncode']==0
        stage_logs[name]=dict(path=str(source/name),sha256=sha(source/name),returncode=0)
    expected={}
    for line in (a.candidate/'outputs.sha256').read_text().splitlines():
        digest,name=line.split();assert re.fullmatch('[a-zA-Z0-9_.-]+',name) and name not in expected
        assert sha(a.candidate/name)==digest;expected[name]=digest
    for label,want in [('before',dict(diagnostic_only='true',native_leaf_accepted='false',setup_checks='0',hold_checks='1',capacitance='0',slew='0',fanout='0')),
                       ('after',dict(diagnostic_only='true',native_leaf_accepted='false',setup_checks='0',hold_checks='0',capacitance='0',slew='0',fanout='0'))]:
        assert dict(row.split('\t',1) for row in (a.candidate/(label+'-summary.tsv')).read_text().splitlines())==want
    assert not (a.candidate/'candidate-native-drc.rpt').read_bytes()
    check=(a.candidate/'after-check.log').read_text().splitlines()
    assert len(check)==5 and all(row.endswith(': OK') for row in check)
    relative=Path('flow/results/nangate45/bv1_block_v1_r/base')
    before=a.source/relative
    manifest=(a.candidate/'before.sha256').read_text().splitlines()
    assert manifest[0].split()[0]==sha(before/'6_final.odb')==old_receipt['outputs'][str(relative/'6_final.odb')]
    assert manifest[1].split()[0]==sha(before/'6_final.sdc')==old_receipt['outputs'][str(relative/'6_final.sdc')]
    assert manifest[3].split()[0]==sha(ROOT/'project/experiments/block_v2/probe_r_postroute_buffer.tcl')
    with (a.candidate/'before.def').open('rb') as f,(a.candidate/'after.def').open('rb') as g:
        geometry=compare_def_lines(f,g)
    evidence=ROOT/'work/YUZE-LU/143/r-input-hold/trace-127'
    index=json.loads((evidence/'index.json').read_text())
    assert index['diagnostic_completed'] and not index['native_leaf_accepted']
    assert min(x['slack_ns'] for x in index['shared_buffer_paths'] if x['path_type']=='max')>.200
    for name,digest in index['files'].items():assert sha(evidence/name)==digest
    contacts=pin_contact_audit((evidence/'buffer-master-pins.tsv').read_text().splitlines(),(a.candidate/'wire-pin-context.tsv').read_text().splitlines())
    a.out.mkdir(parents=True,exist_ok=False);after=a.out/relative;after.mkdir(parents=True)
    receipt=dict(passed=False,top=old['top'],commands=[],inputs={str(a.source/'receipt.json'):sha(a.source/'receipt.json'),str(a.candidate/'outputs.sha256'):sha(a.candidate/'outputs.sha256')})
    for directory in ('project/experiments/block_v2','project/experiments/block_v1','project/experiments/block_feed_v1'):
        for file in (ROOT/directory).rglob('*'):
            if file.is_file() and '__pycache__' not in file.parts:receipt['inputs'][str(file.relative_to(ROOT))]=sha(file)
    flow=copy.deepcopy(old)
    flow.update(passed=False,pipeline_completed=False,final_files={},qualified_hard_macro=False)
    def checked_copy(src,dst):
        digest=sha(src);assert digest==old_receipt['outputs'][str(src.relative_to(a.source))]
        shutil.copyfile(src,dst);assert sha(dst)==digest
    def save():(a.out/'native-flow.json').write_text(json.dumps(flow,indent=2)+'\n')
    def run(cmd,log):
        started=time.time()
        with (a.out/log).open('w') as stream:result=subprocess.run(list(map(str,cmd)),cwd=a.out,stdout=stream,stderr=subprocess.STDOUT)
        receipt['commands'].append(dict(command=list(map(str,cmd)),log=log,sha256=sha(a.out/log),returncode=result.returncode,seconds=time.time()-started))
        assert result.returncode==0,(log,result.returncode)
    try:
        for src in a.source.iterdir():
            if src.is_file() and src.name in old_receipt['outputs'] and src.name not in ('receipt.json','native-flow.json','config.mk'):
                checked_copy(src,a.out/src.name)
        for src in before.iterdir():
            if src.is_file() and (src.name.startswith('issue143-') or src.name in ('1_synth_lec.v','1_2_yosys.v','1_2_yosys.sdc','bv1-input-diodes.tsv','feed-input-receivers.tsv','feed-partition-fanout.tsv')):
                checked_copy(src,after/src.name)
        checked_copy(before/'5_route.sdc',after/'5_route.sdc')
        assert sha(a.source/'config.mk')==old['config_sha256']==old_receipt['outputs']['config.mk']
        config=(a.source/'config.mk').read_text().replace(str(a.source),str(a.out))
        assert str(a.source) not in config
        (a.out/'config.mk').write_text(config)
        shutil.copyfile(a.candidate/'candidate.odb',after/'5_route.odb')
        assert sha(after/'5_route.odb')==expected['candidate.odb']
        for category in ('logs','reports','objects'):(a.out/'flow'/category/'nangate45/bv1_block_v1_r/base').mkdir(parents=True)
        checked_copy(a.source/'flow/reports/nangate45/bv1_block_v1_r/base/5_route_drc.rpt',a.out/'flow/reports/nangate45/bv1_block_v1_r/base/5_route_drc.rpt')
        bound={name:dict(path=str(before/name),sha256=sha(before/name)) for name in ('6_final.odb','6_final.def','6_final.sdc')}
        proof=dict(passed=True,target='place571072',kind='single-combinational-buffer-master',source=str(a.source),source_receipt_sha256=sha(a.source/'receipt.json'),
                   source_files=bound,source_successful_stage_logs=stage_logs,source_final_passed=False,
                   candidate_folder=str(a.candidate),candidate_outputs=expected,candidate_manifest_sha256=sha(a.candidate/'outputs.sha256'),
                   native_whole_drc_zero=True,qualified_hard_macro=False,pin_contacts=contacts,**geometry,
                   scope='Only BUF_X4 to equivalent CLKBUF_X3 at unchanged placement/ports/connections; all routes byte-identical. Original123 final failed; no final success inherited. Fresh native finish/full LEC/RC and all independent gates required.')
        (a.out/'route-repair-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
        wanted={k:(v.replace(str(a.source),str(a.out)) if isinstance(v,str) else v) for k,v in old['actual_variables'].items()}
        flow.update(config_sha256=sha(a.out/'config.mk'),actual_variables=wanted,
                    postroute_repair=dict(source=str(a.source),receipt_sha256=sha(a.source/'receipt.json'),proof_sha256=sha(a.out/'route-repair-proof.json'),
                        fresh_stages=['measured-single-buffer-master'],inherited_successful_native_stages=stages,
                        scope=proof['scope']),fresh_physical_stages=['measured-single-buffer-master'])
        save()
        command=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(a.out/'config.mk'),'WORK_HOME='+str(a.out/'flow'),'NUM_CORES=16']
        for key,value in wanted.items():
            log='variable-'+key+'.log';run(command+['print-'+key],log)
            matches=re.findall(r'(?m)^'+key+r':(.*)$',(a.out/log).read_text());assert len(matches)==1 and matches[0].strip()==str(value)
        observations=[]
        while True:
            available=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
            observations.append(dict(time_unix=time.time(),available_bytes=available,required_bytes=192*1024**3))
            (a.out/'native-final-memory-admission.json').write_text(json.dumps(dict(passed=available>=192*1024**3,observations=observations,
                basis='Prior actual native proof146771828KiB peak;192GiB per full proof. No final proof skipped.'),indent=2)+'\n')
            if available>=192*1024**3:break
            time.sleep(30)
        run(command+['do-finish'],'05-do-finish.log')
        flow['stages'].append('do-finish');flow['fresh_physical_stages'].append('do-finish');flow['postroute_repair']['fresh_stages'].append('do-finish')
        for suffix in ('v','sdc','def','odb','spef'):
            file=after/('6_final.'+suffix);assert file.is_file()
            flow['final_files'][file.name]=dict(path=str(file),sha256=sha(file),bytes=file.stat().st_size)
        for name,row in bound.items():assert sha(row['path'])==row['sha256']
        for name,digest in expected.items():assert sha(a.candidate/name)==digest
        flow.update(passed=True,pipeline_completed=True);save();receipt['passed']=True
    finally:
        receipt['outputs']={str(file.relative_to(a.out)):sha(file) for file in a.out.rglob('*') if file.is_file()}
        (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':main()
