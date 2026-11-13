"""Bind accepted compact macro artifacts to the exact routed database."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

from qualify import sha, source


def checked(folder, name):
    receipt=json.loads((folder/'receipt.json').read_text())
    path=folder/name
    assert receipt['passed'] and receipt['outputs'][name]==sha(path)
    result=json.loads(path.read_text())
    assert result['passed']
    return result


def deliver(final, out):
    sealed=Path((final/'selected.txt').read_text().strip())
    audit=sealed.parent
    _, _, flow, native=source(sealed)
    top=flow['top']
    assert top in ('block_v2_g','block_v2_e_compact')
    physical=checked(audit/'physical','five-macro-physical.json')
    function=checked(final/'function','final-function.json')
    formal=checked(final/'formal','formal.json')
    assert all(report['source_receipt_sha256']==sha(sealed/'receipt.json')
               for report in (physical,function,formal))
    assert all(physical['checks'].values()) and formal['strict_native_lec']['passed']
    assert len(function['initial_runs'])==3
    assert not (audit/'native-whole-drc.rpt').stat().st_size
    assert (audit/'full-deck-count.txt').read_text().strip()=='0'
    assert flow['planned_complete_escape']['passed'] and flow['planned_independent_gds']['passed']
    assert flow['planned_complete_escape']['connected_bits']==len(json.loads((sealed/'pins.json').read_text())['pins'])
    drc_sources={}
    for line in (audit/'drc-source.sha256').read_text().splitlines():
        digest, path=line.split(maxsplit=1)
        path=Path(path)
        assert sha(path)==digest
        drc_sources[path.name]=path
    assert drc_sources['6_final.odb']==native/'6_final.odb'
    assert len(drc_sources)==4
    out.mkdir(parents=True,exist_ok=False)
    raw=Path(flow['raw_source'])
    for path in [*(native/('6_final.'+suffix) for suffix in ('odb','def','sdc','spef','v')),
                 drc_sources['6_final.gds'],drc_sources['full-deck.lyrdb'],
                 sealed/'pins.json',raw/'all-ports.json',raw/'all-ports.gds',raw/'klayout-results.json',
                 audit/'occupancy.json',audit/'physical'/'physical-pins.tsv']:
        shutil.copyfile(path,out/path.name)
    tcl=out/'views.tcl'
    lib='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
    tcl.write_text(f'read_liberty {{{lib}}}\nread_db 6_final.odb\nread_sdc 6_final.sdc\n'
                   'read_spef 6_final.spef\nset_propagated_clock [all_clocks]\n'
                   f'write_abstract_lef -bloat_occupied_layers {top}.lef\n'
                   f'write_timing_model -library_name {top}_tt -cell_name {top} {top}.lib\n')
    with (out/'views.log').open('w') as log:
        subprocess.run(['openroad','-no_init','-exit',tcl],cwd=out,stdout=log,stderr=subprocess.STDOUT,check=True)
    for name in (top+'.lef',top+'.lib'):
        assert (out/name).stat().st_size>0
    evidence=[sealed/'receipt.json',audit/'physical'/'receipt.json',audit/'drc-source.sha256',
              final/'function'/'receipt.json',final/'formal'/'receipt.json']
    index=dict(top=top,leaf_accepted=True,source=str(sealed),die_um=flow['die_um'],
               final_active_um2=physical['active_area_um2'],timing=physical['timing'],
               upper_escape=flow['planned_complete_escape'],
               scope='Native M1-M10 plus all-port M11/M12 finite escape geometry; parent timing and routed product are separate.',
               files={p.name:dict(sha256=sha(p),bytes=p.stat().st_size) for p in sorted(out.iterdir())},
               evidence={str(p):sha(p) for p in evidence})
    (out/'delivery.json').write_text(json.dumps(index,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('final',type=Path)
    parser.add_argument('out',type=Path)
    args=parser.parse_args()
    deliver(args.final.resolve(),args.out.resolve())
