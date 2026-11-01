"""Measured-route partition reproduction and real-spacing negative controls.

These small fixtures cannot qualify R. No original file is edited and no
native marker is filtered, removed or reclassified.
"""
import json
from pathlib import Path
import re


def controls(root,out,candidate,run,sha):
    evidence=root/'work/YUZE-LU/143/r-input-hold/buffer-129'
    index=json.loads((evidence/'index.json').read_text())
    source=candidate/'after.def';expected=index['large_remote_files']['after.def']['sha256'];assert sha(source)==expected
    name='$abc$4429625$new_n602127';record=[]
    with source.open() as f:
        for line in f:
            if line.lstrip().startswith('- '+name+' '):record=[line]
            elif record:record.append(line)
            if record and line.rstrip().endswith(';'):break
    assert record and record[-1].rstrip().endswith(';')
    original=''.join(record);assert '+ ROUTED metal2 ( 80750 1246700 )' in original
    route=original[original.index('+ ROUTED'):]
    (out/'original-sample-net.def.txt').write_text(original)
    base='''VERSION 5.8 ;
DIVIDERCHAR "/" ;
BUSBITCHARS "[]" ;
DESIGN issue143_partition_fixture ;
UNITS DISTANCE MICRONS 2000 ;
DIEAREA ( 0 0 ) ( 6000000 6000000 ) ;
GRID
NETS 1 ;
- sample + USE SIGNAL
'''+route+'END NETS\nEND DESIGN\n'
    platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
    tech=platform/'lef/NangateOpenCellLibrary.tech.lef';assert tech.is_file()
    fixture_results={}
    for label,grid in [('fragmented','GCELLGRID X 0 DO 1052 STEP 5700 ;\nGCELLGRID Y 0 DO 1052 STEP 5700 ;'),
                       ('complete','GCELLGRID X 0 DO 2 STEP 6000000 ;\nGCELLGRID Y 0 DO 2 STEP 6000000 ;')]:
        (out/(label+'.def')).write_text(base.replace('GRID',grid))
        script='set_thread_count 16\nread_lef {'+str(tech)+'}\nread_def {'+str(out/(label+'.def'))+'}\ndrt::check_drc_cmd '+label+'-drc.rpt 0 0 0 0 '+label+'_fixture\n'
        (out/(label+'.tcl')).write_text(script)
        run(['openroad','-no_init','-exit',out/(label+'.tcl')],label+'.log')
        text=(out/(label+'-drc.rpt')).read_text()
        fixture_results[label]=dict(native_drc_count=text.count('violation type:'),native_drc_zero=not text.strip(),report_sha256=sha(out/(label+'-drc.rpt')))
    # Two real narrow gaps: separate nets and a connected same-net U notch.
    negative='''VERSION 5.8 ;
DIVIDERCHAR "/" ;
BUSBITCHARS "[]" ;
DESIGN issue143_spacing_negative ;
UNITS DISTANCE MICRONS 2000 ;
DIEAREA ( 0 0 ) ( 20000 20000 ) ;
GCELLGRID X 0 DO 2 STEP 20000 ;
GCELLGRID Y 0 DO 2 STEP 20000 ;
NETS 3 ;
- real_spacing_a + USE SIGNAL + ROUTED metal2 ( 4000 4000 ) ( * 8000 ) ;
- real_spacing_b + USE SIGNAL + ROUTED metal2 ( 4200 4000 ) ( * 8000 ) ;
- real_notch + USE SIGNAL + ROUTED metal3 ( 8000 12000 ) ( 12000 * )
 NEW metal3 ( 8000 12200 ) ( 12000 * )
 NEW metal3 ( 8000 12000 ) ( * 12200 ) ;
END NETS
END DESIGN
'''
    (out/'spacing-negative.def').write_text(negative)
    script='set_thread_count 16\nread_lef {'+str(tech)+'}\nread_def {'+str(out/'spacing-negative.def')+'}\ndrt::check_drc_cmd spacing-negative-drc.rpt 0 0 0 0 spacing_negative\n'
    (out/'spacing-negative.tcl').write_text(script)
    run(['openroad','-no_init','-exit',out/'spacing-negative.tcl'],'spacing-negative.log')
    text=(out/'spacing-negative-drc.rpt').read_text()
    found=re.findall(r'violation type: Metal Spacing\n\s*srcs: ([^\n]+)',text)
    different=any('net:real_spacing_a' in row and 'net:real_spacing_b' in row for row in found)
    notch=any(row.strip()=='net:real_notch' for row in found)
    assert different and notch,'Actual same-net and foreign-net spacing controls must both fail'
    assert sha(source)==expected
    reproduced=fixture_results['fragmented']['native_drc_count']>0 and fixture_results['complete']['native_drc_zero']
    return dict(partition_fixture_results=fixture_results,partition_effect_reproduced=reproduced,
                real_foreign_net_spacing_detected=different,real_same_net_notch_detected=notch,
                original_source_unchanged=True,source_def_sha256=expected,source_net=name,
                only_grid_diff_between_positive_fixtures=True,technology_sha256=sha(tech),
                native_leaf_accepted=False,qualified=False)
