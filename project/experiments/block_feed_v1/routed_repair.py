"""Repair one measured final M10 route; rerun native finish/RCX and all gates.

No previous route's qualification transfers. The exact complete non-target DEF
must be unchanged, and all target connectivity must be identical.
"""
import copy
import json
from pathlib import Path
import re
import shutil

from io_slots import file_sha as sha


def split_net(path):
    text=path.read_text()
    begin=text.index('    - dout[58] ( PIN dout[58] )')
    match=re.search(r'(?m)^    - ',text[begin+1:]); assert match
    end=begin+1+match.start()
    return text[:begin]+text[end:],text[begin:end]


def repair(root,a,run,journal):
    raw,out=a.source,a.out
    r=json.loads((raw/'receipt.json').read_text())
    assert r['passed'] and journal['passed'] and journal['pipeline_completed']
    assert journal['top']=='block_feed_s_macro'
    assert sha(raw/'native-flow.json')==r['outputs']['native-flow.json']
    for p,digest in journal['rtl_sha256'].items():assert sha(root/p)==digest
    relative='flow/results/nangate45/bv1_block_feed_s_macro/base'
    before,after=raw/relative,out/relative;after.mkdir(parents=True)
    bound={}
    names=['6_final.odb','6_final.def','5_route.sdc','1_synth_lec.v','1_2_yosys.v','1_2_yosys.sdc',
           'bv1-input-diodes.tsv','feed-input-receivers.tsv','feed-partition-fanout.tsv']
    for name in names:
        p=before/name;digest=sha(p)
        assert digest==r['outputs'][str(p.relative_to(raw))]
        bound[name]=dict(path=str(p),sha256=digest)
        if not name.startswith('6_final.'):shutil.copyfile(p,after/name)
    shutil.copyfile(before/'5_route.sdc',after/'5_route.sdc')
    config_names=['pins.json','pins.tcl','input.sdc','input.v','input-diodes.tcl',
                  'partition-fanout.tcl','electrical-closure.tcl']
    for name in config_names:
        assert sha(raw/name)==r['outputs'][name]
        shutil.copyfile(raw/name,out/name)
    config=(raw/'config.mk').read_text()
    assert sha(raw/'config.mk')==journal['config_sha256']==r['outputs']['config.mk']
    for name in config_names:config=config.replace(str(raw/name),str(out/name))
    (out/'config.mk').write_text(config)
    hook=root/'project/experiments/block_feed_v1/measured_s_route.tcl'
    script='set_thread_count 16\nread_db {'+str(before/'6_final.odb')+'}\nwrite_def before-route.def\n'
    script+=hook.read_text()
    script+='write_def after-route.def\ndrt::check_drc_cmd repaired-native-drc.rpt 0 0 0 0 repaired_native_drc\n'
    script+='write_db {'+str(after/'5_route.odb')+'}\n'
    (out/'repair-route.tcl').write_text(script)
    run(['openroad','-no_init','-exit',out/'repair-route.tcl'],'repair-route.log')
    assert not (out/'repaired-native-drc.rpt').read_text().strip()
    unchanged,old=split_net(out/'before-route.def');same,new=split_net(out/'after-route.def')
    assert unchanged==same and old!=new
    assert old.splitlines()[0]==new.splitlines()[0]
    assert '1756990 835340' in old and '1756990 835340' not in new
    proof=dict(passed=True,target='dout[58]',source=str(raw),source_receipt_sha256=sha(raw/'receipt.json'),
        source_files=bound,hook_sha256=sha(hook),unchanged_non_target_def_sha256=__import__('hashlib').sha256(unchanged.encode()).hexdigest(),
        before_def_sha256=sha(out/'before-route.def'),after_def_sha256=sha(out/'after-route.def'),
        identical_non_target_geometry=True,identical_target_terminal_connections=True,old_net=old,new_net=new,
        native_whole_drc_zero=True,qualified_hard_macro=False)
    (out/'route-repair-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    result=copy.deepcopy(journal)
    result.update(passed=False,pipeline_completed=False,final_files={},config_sha256=sha(out/'config.mk'),
        postroute_repair=dict(source=str(raw),receipt_sha256=sha(raw/'receipt.json'),proof_sha256=sha(out/'route-repair-proof.json'),
            inherited_successful_native_stages=journal['stages'],fresh_stages=['measured-single-net-M10-route'],
            scope='Original final route is not independently qualified; exact single-net geometry repair, fresh native finish/RCX and all final gates required'),
        fresh_physical_stages=['measured-single-net-M10-route'])
    wanted={k:(v.replace(str(raw)+'/',str(out)+'/') if isinstance(v,str) else v) for k,v in journal['actual_variables'].items()}
    result['actual_variables']=wanted
    def save():(out/'native-flow.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    for category in ('logs','reports','objects'):(out/'flow'/category/'nangate45/bv1_block_feed_s_macro/base').mkdir(parents=True)
    cmd=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(out/'config.mk'),'WORK_HOME='+str(out/'flow'),'NUM_CORES=16']
    for key,value in wanted.items():
        log='variable-'+key+'.log';run(cmd+['print-'+key],log)
        actual=re.search(r'(?m)^'+key+r': (.+)$',(out/log).read_text()).group(1).strip();assert actual==value
    run(cmd+['do-finish'],'fresh-do-finish.log')
    result['fresh_physical_stages'].append('do-finish');result['postroute_repair']['fresh_stages'].append('do-finish')
    for suffix in ('v','sdc','def','odb','spef'):
        p=after/('6_final.'+suffix);assert p.is_file()
        result['final_files'][p.name]=dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)
    for row in bound.values():assert sha(row['path'])==row['sha256']
    result.update(passed=True,pipeline_completed=True);save()
