"""Read-only diagnosis of fresh-route, STA-cache and resizer initialization RC."""
import json
from pathlib import Path
import re


def execute(root,source,run_tcl,track,digest,platform,checkpoint,clear):
    assert re.fullmatch(r'[a-zA-Z0-9_-]+',checkpoint)
    manifest={n[2:]:h for h,n in (line.split(None,1) for line in (source/'output.sha256').read_text().splitlines())}
    meta=json.loads((source/'experiment.json').read_text())
    text='read_liberty {'+str(track(platform/'lib/NangateOpenCellLibrary_typical.lib'))+'}\n'
    for k in (['act','mxu'] if meta['kind']=='split' else ['merged']):
        view=meta['views'][k];text+='read_liberty {'+str(track(Path(view['view'])/(view['name']+'.lib')))+'}\n'
    for ext,cmd in [('odb','read_db'),('sdc','read_sdc')]:
        p=source/meta['result_relative']/(checkpoint+'.'+ext)
        assert digest(p)==manifest[p.relative_to(source).as_posix()]
        text+=cmd+' {'+str(track(p))+'}\n'
    text+='source {'+str(track(platform/'setRC.tcl'))+'}\n'
    text+='set_propagated_clock [all_clocks]\nset_routing_layers -signal metal2-metal10 -clock metal4-metal10\n'
    text+='set signal_wires {}\nforeach net [[ord::get_db_block] getNets] {if {[$net getSigType] ni {POWER GROUND} && [$net getWire] ne "NULL"} {lappend signal_wires [$net getWire]}}\n'
    text+='puts "LOADED_REGULAR_SIGNAL_WIRES [llength $signal_wires]"\n'
    if clear:text+='foreach wire $signal_wires {odb::dbWire_destroy $wire}\n'
    text+='pin_access\nglobal_route -congestion_iterations 30\nestimate_parasitics -global_routing\n'
    stages=['before_timing','after_timing','after_preamble','after_repeat_route']
    for stage in stages:
        if stage=='after_preamble':text+='rsz::resize_slack_preamble\nestimate_parasitics -global_routing\n'
        if stage=='after_repeat_route':text+='global_route -congestion_iterations 30\nestimate_parasitics -global_routing\n'
        if stage!='before_timing':text+='report_worst_slack -max -digits 9\nreport_worst_slack -min -digits 9\n'
        text+='report_check_types -max_capacitance -max_slew -max_count 1000 -digits 9 -no_line_splits > {'+str(root/(stage+'.rpt'))+'}\n'
    run_tcl('grt-consistency',text)
    output={}
    for stage in stages:
        t=(root/(stage+'.rpt')).read_text()
        rows=re.findall(r'^\s*(\S+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+\((MET|VIOLATED)\)',t,re.M)
        output[stage]=dict(violations=[r for r in rows if r[-1]=='VIOLATED'],
            watched=[r for r in rows if r[0] in ['wire13222/Z','wire13193/Z','wire3760/Z']])
    (root/'grt-consistency.json').write_text(json.dumps(output,indent=2)+'\n')
    snippets={}
    for relative in ['src/rsz/src/Resizer.cc','src/est/src/EstimateParasitics.cpp']:
        p=Path('/OpenROAD-flow-scripts/tools/OpenROAD')/relative
        if p.is_file():
            track(p);t=p.read_text()
            for key in ['void Resizer::resizeSlackPreamble','void Resizer::resizePreamble','void EstimateParasitics::estimateParasitics']:
                start=t.find(key)
                if start>=0:snippets[relative+' '+key]=t[start:start+6000]
    (root/'bundled-source-snippets.json').write_text(json.dumps(snippets,indent=2)+'\n')
