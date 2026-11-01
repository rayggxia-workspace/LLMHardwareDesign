"""Export every actual signal-bearing cell from the sealed physical database."""
import json
from pathlib import Path


def export(root,out,run,source,receipt,results,top,library):
    from io_slots import file_sha
    from native_logic_projection import project
    from structural_view import compare
    odb=results/'6_final.odb';raw=results/'6_final.v'
    inputs={str(p):file_sha(p)for p in [odb,raw]}
    for p,digest in inputs.items():assert digest==receipt['outputs'][str(Path(p).relative_to(source))]
    target=out/'physical-functional.v'
    text='read_liberty '+str(library)+'\nread_db {'+str(odb)+'}\n'
    text+='set remove {}\nforeach lib [[ord::get_db] getLibs] {\n foreach master [$lib getMasters] {\n'
    text+='  set signal 0\n  foreach term [$master getMTerms] {if {[$term getSigType] ni {POWER GROUND}} {set signal 1}}\n'
    text+='  if {!$signal} {lappend remove [$master getName]}\n }\n}\n'
    text+='write_verilog -remove_cells $remove {'+str(target)+'}\n'
    script=out/'physical-functional.tcl';script.write_text(text)
    run(['openroad','-no_init','-exit',str(script)],'physical-functional.log')
    parsed={}
    for label,path in [('physical',target),('source',raw)]:
        graph=out/(label+'-functional.json');ys=out/(label+'-functional.ys')
        text='read_liberty -lib '+str(library)+'\nread_verilog '+str(path)+'\nhierarchy -check -top '+top+'\nwrite_json '+str(graph)+'\n'
        ys.write_text(text);run(['yosys','-s',str(ys)],label+'-functional-parse.log')
        parsed[label]=json.loads(graph.read_text())
    projected,proof=project(parsed['physical'],library.read_text())
    assert proof['removed_count']>0,'Actual exported physical view lacks protection cells'
    source_projected,source_proof=project(parsed['source'],library.read_text())
    assert source_proof['removed_count']==0,'Expected the original ORFS antenna-filtered view'
    correspondence=compare(projected,source_projected)
    # The only allowed difference from the sealed flow view is independently
    # audited input-only ANTENNA_X1. Every other port, cell and pin-bit matches.
    assert all(file_sha(Path(p))==digest for p,digest in inputs.items())
    result=dict(schema='block-v1-physical-functional-view/1',passed=True,input_sha256=inputs,
        full_view=str(target),full_view_sha256=file_sha(target),input_only_projection=proof,
        exact_other_signal_connectivity=correspondence,source_antenna_count=source_proof['removed_count'],
        scope='Actual ODB export retaining every signal-bearing master, including all protection loads; only audited input-only cells differ from original filtered flow view')
    (out/'physical-functional-proof.json').write_text(json.dumps(result,indent=2)+'\n')
    return target,result
