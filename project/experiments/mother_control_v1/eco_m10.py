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

def canonical_nets(text, section):
    body=text.split('\n'+section+' ',1)[1].split('\nEND '+section,1)[0]
    result={}
    for name,entry in re.findall(r'^\s*- (\S+) (.*?);',body,re.M|re.S):
        head,separator,tail=entry.partition('+');assert separator
        connections=tuple(sorted(re.findall(r'\(\s*([^()]+?)\s*\)',head)))
        assert name not in result
        result[name]=(connections,tuple(tail.split()))
    return result

def encode_paths(paths):
    lines=['set block [ord::get_db_block]','set tech [ord::get_db_tech]',
           'set net [$block findNet {local_image_id0_i[4]}]',
           'odb::dbWire_destroy [$net getWire]',
           'set wire [odb::dbWire_create $net]',
           'set encoder [odb::dbWireEncoder]','$encoder begin $wire']
    for layer,body in paths:
        lines.append('$encoder newPath [$tech findLayer '+layer+'] ROUTED')
        tokens=list(re.finditer(r'\(\s*([*0-9]+)\s+([*0-9]+)(?:\s+(-?[0-9]+))?\s*\)|(\w+)',body))
        assert not re.sub(r'\(\s*([*0-9]+)\s+([*0-9]+)(?:\s+(-?[0-9]+))?\s*\)|(\w+)','',body).strip()
        x=y=None
        for token in tokens:
            if token[4]:
                via=token[4]
                lines.extend(['set via [$block findVia '+via+']',
                    'if {$via ne "NULL"} {$encoder addVia $via} else {',
                    ' set via [$tech findVia '+via+']',
                    ' if {$via eq "NULL"} {error "Missing original via '+via+'"}',
                    ' $encoder addTechVia $via','}'])
            else:
                x=x if token[1]=='*' else int(token[1]);y=y if token[2]=='*' else int(token[2]);assert x is not None and y is not None
                lines.append('$encoder addPoint '+str(x)+' '+str(y)+(' '+token[3] if token[3] else ''))
    lines.append('$encoder end')
    return '\n'.join(lines)+'\n'

def main():
    p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    source=a.candidate.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    original=source/'flow/results/nangate45/mother_control_64/base';target=out/original.relative_to(source);target.mkdir(parents=True)
    name='local_image_id0_i[4]'
    snapshot=out/'snapshot.tcl';snapshot.write_text('read_db {'+str(original/'5_route.odb')+'}\nwrite_def {'+str(out/'before.def')+'}\n')
    with (out/'snapshot.log').open('w') as log:subprocess.run(['openroad','-no_init','-exit',str(snapshot)],stdout=log,stderr=subprocess.STDOUT,check=True)
    text=(out/'before.def').read_text();old=find_net(text,name)
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
    # Encode the sole changed wire directly in the original database. Full
    # DEF import loses non-DEF router state; incremental import skips wires.
    delta=out/'eco.def';delta.write_text(text.replace(old,'    '+replacement.rstrip()))
    new_paths=[('metal10','( 867390 1388940 ) ( 864190 * ) ( * 1464900 ) ( 870590 * ) ( * 1478540 0 )'),*kept]
    tcl=out/'eco.tcl';tcl.write_text('read_db {'+str(original/'5_route.odb')+'}\n'+encode_paths(new_paths)+'write_def {'+str(out/'after.def')+'}\nwrite_db {'+str(target/'5_route.odb')+'}\n')
    with (out/'eco.log').open('w') as log:subprocess.run(['openroad','-no_init','-exit',str(tcl)],stdout=log,stderr=subprocess.STDOUT,check=True)
    before=(out/'before.def').read_text();after=(out/'after.def').read_text()
    assert '+ ROUTED metal10' in find_net(after,name),'ECO wire was not imported'
    # OpenDB reverses linked-list terminal order on full DEF import. Compare
    # unordered terminal membership, while retaining exact ordered geometry
    # tokens, instance placement, pin shapes, rows, tracks and native vias.
    assert before.split('\nSPECIALNETS ')[0]==after.split('\nSPECIALNETS ')[0]
    assert canonical_nets(before,'SPECIALNETS')==canonical_nets(after,'SPECIALNETS')
    old_nets=canonical_nets(before,'NETS');new_nets=canonical_nets(after,'NETS')
    assert old_nets[name][0]==new_nets[name][0]
    del old_nets[name];del new_nets[name]
    assert old_nets==new_nets,'ECO altered unrelated routed nets'
    imported=re.findall(r'(?:\+ ROUTED|NEW)\s+(\w+)\s+(.*?)(?=\s+NEW\s|\s*;\s*$)',find_net(after,name),re.S)
    canonical=lambda paths:sorted((layer,tuple(body.split())) for layer,body in paths if layer!='metal10')
    assert canonical(routes)==canonical(imported),'ECO altered original lower-layer route'
    for n in ('5_route.sdc','1_synth_lec.v'):shutil.copyfile(original/n,target/n)
    shutil.copyfile(source/'config.mk',out/'config.mk')
    inputs=json.loads((source/'inputs.json').read_text());inputs.update(qualified=False,m10_eco=dict(net=name,original_odb_sha256=sha(original/'5_route.odb'),delta_sha256=sha(delta),only_one_net_changed=True,placement_and_other_nets_unchanged=True,source_candidate=str(source),script_sha256=sha(Path(__file__))))
    (out/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
    command=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(out/'config.mk'),'WORK_HOME='+str(out/'flow'),'NUM_CORES='+os.environ['SLURM_CPUS_PER_TASK']]
    for stage in ('do-finish','do-gds'):
        with (out/(stage+'.log')).open('w') as log:subprocess.run(command+[stage],stdout=log,stderr=subprocess.STDOUT,check=True)
    assert sha(original/'5_route.odb')==inputs['m10_eco']['original_odb_sha256']

if __name__=='__main__':main()
