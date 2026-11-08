"""Prepare actual native-circuit STA with original constraints and fresh upper RC.

Only constraints for ports that became internal wires are removed. No clock,
Liberty limit, remaining I/O delay or functional false path is relaxed.
"""
import argparse
import json
from pathlib import Path
import re

from native_inventory import sha


def prepare(config,binding,out):
    out.mkdir()
    for kind in ('odb','spef','sdc','netlist'):
        ref=config[kind];assert sha(ref['path'])==ref['sha256'],kind+' source changed'
    for ref in config['liberties']+config['lefs']:
        assert sha(ref['path'])==ref['sha256'],'source view changed'
    ends={p for n in binding['nets'].values() for p in [n['driver']]+n['sinks']}
    links=[]
    for net in binding['nets'].values():
        if len(net['sinks'])!=1:raise ValueError('native single-patch netlist stitch needs a fanout-aware exporter for this input')
        links.append(net['driver']+'\t'+net['sinks'][0]+'\n')
    (out/'stitched-ports.tsv').write_text(''.join(links))
    original=Path(config['sdc']['path']).read_text();kept=[];removed=[]
    for line in original.splitlines(keepends=True):
        ports=re.findall(r'\[get_ports\s+\{([^}]+)\}\]',line)
        requested=[p for span in ports for p in span.split()]
        if ends.intersection(requested):
            assert len(ports)==1 and len(requested)==1,'mixed boundary constraint needs explicit rewriting'
            assert re.match(r'^set_(input_delay|output_delay|load|input_transition|driving_cell)\s',line),'unexpected removed constraint'
            removed.append(line.rstrip())
        else:kept.append(line)
    (out/'input.sdc').write_text(''.join(kept))
    (out/'constraint-audit.json').write_text(json.dumps({'original_sha256':sha(config['sdc']['path']),
        'retained_sdc_sha256':sha(out/'input.sdc'),'removed_internal_port_constraints':removed,
        'internal_ports':sorted(ends),'other_constraints_preserved_verbatim':True},indent=2)+'\n')
    # Existing exporter operates on actual ODB terminals and includes antenna
    # cells; it removes only physical-only masters without signal terminals.
    tcl=['set ::env(CFJ_FINAL_ODB) {'+config['odb']['path']+'}',
         'set ::env(CFJ_OVERLAY_DIR) {'+str(out)+'}',
         'source project/experiments/cfj_leaf_base/stitch_netlist.tcl']
    (out/'stitch.tcl').write_text('\n'.join(tcl)+'\n')
    sta=[]
    for ref in config['liberties']:sta.append('read_liberty {'+ref['path']+'}')
    for ref in config['lefs']:sta.append('read_lef {'+ref['path']+'}')
    sta+=['read_verilog {'+str(out/'stitched-ports.v')+'}', 'link_design {'+config['top']+'}',
          'read_sdc {'+str(out/'input.sdc')+'}',
          'read_spef $::env(ROUTER_STITCHED_SPEF)','set_propagated_clock [all_clocks]',
          'set stem $::env(ROUTER_STA_STEM)',
          'report_parasitic_annotation -report_unannotated > $stem-annotation.rpt',
          'report_checks -path_delay min_max -group_path_count 30 -format full_clock_expanded -digits 9 > $stem-paths.rpt',
          'report_worst_slack -max -digits 9 > $stem-summary.rpt',
          'report_worst_slack -min -digits 9 >> $stem-summary.rpt',
          'report_check_types -max_slew -max_capacitance -max_fanout -violators -digits 9 >> $stem-summary.rpt',
          'sta::find_timing','set counts [open $stem-counts.tsv w]',
          'puts $counts "setup\t[sta::endpoint_violation_count max]"',
          'puts $counts "hold\t[sta::endpoint_violation_count min]"',
          'foreach kind {capacitance slew fanout} {puts $counts "$kind\t[sta::max_${kind}_violation_count]"}',
          'close $counts']
    (out/'sta.tcl').write_text('\n'.join(sta)+'\n')
    (out/'sources.json').write_text(json.dumps(config,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('config','binding','output'):p.add_argument(name,type=Path)
    a=p.parse_args();prepare(json.loads(a.config.read_text()),json.loads(a.binding.read_text()),a.output)
