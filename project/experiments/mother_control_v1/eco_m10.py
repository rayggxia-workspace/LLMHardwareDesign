"""Replace one M10 trunk; preserve every other physical net and all placement.

This is a frozen-candidate ECO, not an automatic general-purpose router.
The exact original endpoints and coordinates are checked before modification.
It produces an unqualified candidate needing fresh extraction and all gates.
"""
import argparse, hashlib, json, os, re, shutil, subprocess
from pathlib import Path

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def net_section(text):
    return text[text.index('\nNETS '):text.index('\nEND NETS')]

def find_net(text, name):
    matches = list(re.finditer(r'^\s*- '+re.escape(name)+r'\s.*?;',net_section(text),re.M|re.S))
    assert len(matches)==1
    return matches[0].group(0)

def main():
    p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    source=a.candidate.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    original=source/'flow/results/nangate45/mother_control_64/base';target=out/original.relative_to(source);target.mkdir(parents=True)
    name='local_image_id0_i[4]'
    text=(original/'6_final.def').read_text();old=find_net(text,name)
    assert '( 867390 1388940 ) via9_0' in old
    assert '( PIN '+name+' )' in old and '( hold14183 A )' in old
    routes=re.findall(r'(?:\+ ROUTED|NEW)\s+(\w+)\s+(.*?)(?=\s+NEW\s|\s*;\s*$)',old,re.S)
    assert len(routes)==29, len(routes)
    kept=[(layer,body.strip()) for layer,body in routes if layer!='metal10']
    assert len(kept)==18, len(kept)
    # At the original via9 landing, go two native tracks left, then return
    # to the unchanged original terminal above the adjacent terminal rows.
    replacement='- '+name+old.split(name,1)[1].split('+ ROUTED',1)[0]
    replacement+=' + ROUTED metal10 ( 867390 1388940 ) ( 864190 * ) ( * 1464900 ) ( 870590 * ) ( * 1478540 0 )\n'
    replacement+=''.join(' NEW '+layer+' '+body+'\n' for layer,body in kept)+' ;\n'
    delta=out/'eco.def';delta.write_text('VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\nDESIGN mother_control_64 ;\nUNITS DISTANCE MICRONS 2000 ;\nNETS 1 ;\n'+replacement+'END NETS\nEND DESIGN\n')
    tcl=out/'eco.tcl';tcl.write_text('read_db {'+str(original/'5_route.odb')+'}\nwrite_def {'+str(out/'before.def')+'}\nset net [[ord::get_db_block] findNet {'+name+'}]\nif {$net eq "NULL"} {error "ECO net missing"}\nodb::dbWire_destroy [$net getWire]\nread_def -incremental {'+str(delta)+'}\nwrite_def {'+str(out/'after.def')+'}\nwrite_db {'+str(target/'5_route.odb')+'}\n')
    with (out/'eco.log').open('w') as log:subprocess.run(['openroad','-no_init','-exit',str(tcl)],stdout=log,stderr=subprocess.STDOUT,check=True)
    before=(out/'before.def').read_text();after=(out/'after.def').read_text()
    assert before.replace(find_net(before,name),'\nECO_NET\n')==after.replace(find_net(after,name),'\nECO_NET\n'),'ECO altered unrelated geometry/connectivity'
    for n in ('5_route.sdc','1_synth_lec.v'):shutil.copyfile(original/n,target/n)
    shutil.copyfile(source/'config.mk',out/'config.mk')
    inputs=json.loads((source/'inputs.json').read_text());inputs.update(qualified=False,m10_eco=dict(net=name,original_odb_sha256=sha(original/'5_route.odb'),delta_sha256=sha(delta),only_one_net_changed=True,placement_and_other_nets_unchanged=True,source_candidate=str(source),script_sha256=sha(Path(__file__))))
    (out/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
    command=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(out/'config.mk'),'WORK_HOME='+str(out/'flow'),'NUM_CORES='+os.environ['SLURM_CPUS_PER_TASK']]
    for stage in ('do-finish','do-gds'):
        with (out/(stage+'.log')).open('w') as log:subprocess.run(command+[stage],stdout=log,stderr=subprocess.STDOUT,check=True)
    assert sha(original/'5_route.odb')==inputs['m10_eco']['original_odb_sha256']

if __name__=='__main__':main()
