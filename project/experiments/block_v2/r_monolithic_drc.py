"""Diagnostic whole-die native GC, without a worker boundary inside the die.

No physical shape, connection, rule, marker or source database is changed.
The ordinary fragmented report remains evidence; this is not acceptance.
"""
import hashlib
from itertools import zip_longest
import json
from pathlib import Path
import re
import time


def compare_grid_only(before, after):
    kept=hashlib.sha256();a_grid=[];b_grid=[]
    def filtered(path, rows):
        with Path(path).open('rb') as f:
            for line in f:
                if line.startswith(b'GCELLGRID '):rows.append(line);continue
                yield line
    for a,b in zip_longest(filtered(before,a_grid),filtered(after,b_grid)):
        assert a is not None and a==b,'Physical DEF bytes changed'
        kept.update(a)
    assert a_grid==[b'GCELLGRID X 0 DO 1052 STEP 5700 ;\n',b'GCELLGRID Y 0 DO 1052 STEP 5700 ;\n']
    assert b_grid==[b'GCELLGRID X 0 DO 2 STEP 6000000 ;\n',b'GCELLGRID Y 0 DO 2 STEP 6000000 ;\n']
    return dict(passed=True,unchanged_all_non_gcellgrid_def_sha256=kept.hexdigest(),
                before_grid=[v.decode().strip() for v in a_grid],after_grid=[v.decode().strip() for v in b_grid],
                identical_physical_geometry_and_connections=True)


def diagnostic(root,out,candidate,run,sha):
    evidence=root/'work/YUZE-LU/143/r-input-hold/buffer-129'
    index=json.loads((evidence/'index.json').read_text())
    for n,h in index['files'].items():assert sha(evidence/n)==h
    odb=candidate/'candidate.odb';expected=index['large_remote_files']['candidate.odb']['sha256'];assert sha(odb)==expected
    observations=[]
    while True:
        available=int(next(v.split()[1] for v in Path('/proc/meminfo').read_text().splitlines() if v.startswith('MemAvailable:')))*1024
        observations.append(dict(time_unix=time.time(),available_bytes=available,required_bytes=384*1024**3))
        (out/'memory-admission.json').write_text(json.dumps(dict(passed=available>=384*1024**3,observations=observations),indent=2)+'\n')
        if available>=384*1024**3:break
        time.sleep(30)
    # An isolated fixture uses the same native unmodified technology/rules and
    # the same one-cell complete-die partition. Its intentional short must fail.
    negative='''VERSION 5.8 ;
DIVIDERCHAR "/" ;
BUSBITCHARS "[]" ;
DESIGN issue143_native_negative ;
UNITS DISTANCE MICRONS 2000 ;
DIEAREA ( 0 0 ) ( 20000 20000 ) ;
GCELLGRID X 0 DO 2 STEP 20000 ;
GCELLGRID Y 0 DO 2 STEP 20000 ;
NETS 2 ;
- issue143_negative_a + USE SIGNAL + ROUTED metal2 ( 4000 6000 ) ( 12000 6000 ) ;
- issue143_negative_b + USE SIGNAL + ROUTED metal2 ( 8000 4000 ) ( 8000 10000 ) ;
END NETS
END DESIGN
'''
    (out/'negative.def').write_text(negative)
    platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
    tech=platform/'lef/NangateOpenCellLibrary.tech.lef';assert tech.is_file()
    negscript='set_thread_count 16\nread_lef {'+str(tech)+'}\nread_def {'+str(out/'negative.def')+'}\ndrt::check_drc_cmd negative-drc.rpt 0 0 0 0 native_negative\n'
    (out/'negative.tcl').write_text(negscript)
    run(['openroad','-no_init','-exit',out/'negative.tcl'],'negative.log')
    neg=(out/'negative-drc.rpt').read_text()
    assert re.search(r'violation type: Short\n\s*srcs:.*net:issue143_negative_a.*net:issue143_negative_b',neg) or re.search(r'violation type: Short\n\s*srcs:.*net:issue143_negative_b.*net:issue143_negative_a',neg)
    script='set_thread_count 16\nread_db {'+str(odb)+'}\n'+'''
set b [ord::get_db_block]
set die [$b getDieArea]
if {[$b getDbUnitsPerMicron]!=2000 || [$die xMin]!=0 || [$die yMin]!=0 || [$die xMax]!=6000000 || [$die yMax]!=6000000} {error "Unexpected complete die"}
write_def before.def
set g [$b getGCellGrid]
if {[$g getNumGridPatternsX]!=1 || [$g getNumGridPatternsY]!=1} {error "Unexpected source grid"}
$g resetGrid
$g addGridPatternX 0 2 6000000
$g addGridPatternY 0 2 6000000
if {[$g getGridX] ne {0 6000000} || [$g getGridY] ne {0 6000000}} {error "Whole-die grid readback failed"}
write_def grid-only.def
drt::check_drc_cmd native-monolithic-drc.rpt 0 0 0 0 native_monolithic_drc
puts WHOLE_DIE_NATIVE_DRC_COMPLETE
'''
    (out/'monolithic.tcl').write_text(script)
    run(['openroad','-no_init','-exit',out/'monolithic.tcl'],'monolithic.log')
    proof=compare_grid_only(out/'before.def',out/'grid-only.def')
    (out/'grid-only-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    text=(out/'native-monolithic-drc.rpt').read_text();assert sha(odb)==expected
    return dict(monolithic_native_diagnostic=True,native_drc_count=text.count('violation type:'),native_drc_zero=not text.strip(),
                original_source_unchanged=True,candidate_odb_sha256=expected,grid_only_proof=proof,
                complete_die_box_dbu=[0,0,6000000,6000000],one_complete_native_worker=True,
                intentional_short_detected=True,technology_sha256=sha(tech),qualified=False,native_leaf_accepted=False)
