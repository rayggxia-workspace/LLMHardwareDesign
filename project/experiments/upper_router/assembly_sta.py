"""Prepare real flat-assembly STA, preserving supplied resource constraints."""
import argparse
import json
from pathlib import Path
import re
from native_inventory import sha


def translate_sdc(raw,group,template,internal):
    clocks={n:group+'__'+n for n in re.findall(r'(?m)^create_clock\s+-name\s+(\S+)',raw)}
    assert clocks,'native clocks absent'
    kept=[];removed=[]
    allowed={'create_clock','current_design','set_clock_transition','set_clock_uncertainty',
             'set_propagated_clock','set_input_delay','set_output_delay','set_load','set_driving_cell','set_false_path'}
    for line in raw.replace('\\\n',' ').splitlines():
        if not line.strip() or line.lstrip().startswith('#'):kept.append(line);continue
        command=line.split()[0];assert command in allowed,('unsupported native constraint',line)
        if command=='current_design':continue
        ports=[p for s in re.findall(r'\[get_ports\s+\{([^}]+)\}\]',line) for p in s.split()]
        if internal.intersection(ports):
            assert len(ports)==1 and command in {'set_input_delay','set_output_delay','set_load','set_driving_cell'}
            removed.append(line);continue
        queries=[]
        def query(m):
            kind,values=m[1],m[2];assert kind in {'ports','pins','cells','clocks'}
            names=values.split()
            # The prefix is part of one flat identifier, not an instance path.
            rewritten=[clocks[n] if kind=='clocks' else group+r'\/'+n for n in names]
            queries.append('[get_'+kind+' {'+' '.join(rewritten)+'}]')
            return '@QUERY'+str(len(queries)-1)+'@'
        line=re.sub(r'\[get_(\w+)\s+\{([^}]+)\}\]',query,line)
        assert '[get_' not in line,'unsupported collection syntax'
        for old,new in clocks.items():line=re.sub(r'(?<![\w/])'+re.escape(old)+r'(?![\w/])',lambda _:new,line)
        line=re.sub(r'(-lib_cell\s+)(\S+)',lambda m:m[1]+'SRC_'+template+'_'+m[2],line)
        for i,q in enumerate(queries):line=line.replace('@QUERY'+str(i)+'@',q)
        kept.append(line)
    return '\n'.join(kept)+'\n',removed


def prepare(base,binding,configs,flat,out):
    out.mkdir();internal={p for n in binding['nets'].values() for p in [n['driver']]+n['sinks']}
    constraints=['current_design routed_resource_assembly\n'];audits=[]
    for a in base['assemblies']:
        group,template=a['id'],a['template'];ref=configs[template]['sdc'];assert sha(ref['path'])==ref['sha256']
        selected={p.split('/',1)[1] for p in internal if p.startswith(group+'/')}
        text,removed=translate_sdc(Path(ref['path']).read_text(),group,template,selected)
        constraints.append(text);audits.append({'group':group,'source':ref,'removed_internal_port_constraints':removed})
    (out/'input.sdc').write_text(''.join(constraints))
    views=json.loads((flat/'views.json').read_text())
    proof=json.loads((flat/'source-proof.json').read_text())
    tech=proof['technology'];assert sha(tech['path'])==tech['sha256']
    tcl=['read_lef {'+tech['path']+'}']
    for template,group in sorted(views.items()):
        for ref in group['views']['lefs']:
            assert sha(ref['path'])==ref['sha256'];tcl.append('read_lef {'+ref['path']+'}')
        for ref in group['views']['liberties']:
            assert sha(ref['path'])==ref['sha256'];tcl.append('read_liberty {'+ref['path']+'}')
    netlist=flat/'assembled.v'
    tcl+=['read_verilog {'+str(netlist)+'}','link_design routed_resource_assembly',
          'read_sdc {'+str(out/'input.sdc')+'}','read_spef $::env(ROUTER_STITCHED_SPEF)',
          'set_propagated_clock [all_clocks]','set stem $::env(ROUTER_STA_STEM)',
          'report_parasitic_annotation -report_unannotated > $stem-annotation.rpt',
          'report_checks -path_delay min_max -group_path_count 30 -format full_clock_expanded -digits 9 > $stem-paths.rpt',
          'report_worst_slack -max -digits 9 > $stem-summary.rpt',
          'report_worst_slack -min -digits 9 >> $stem-summary.rpt',
          'report_check_types -max_slew -max_capacitance -max_fanout -violators -digits 9 >> $stem-summary.rpt',
          'sta::find_timing','set f [open $stem-counts.tsv w]',
          'puts $f "setup\t[sta::endpoint_violation_count max]"','puts $f "hold\t[sta::endpoint_violation_count min]"',
          'foreach kind {capacitance slew fanout} {puts $f "$kind\t[sta::max_${kind}_violation_count]"}', 'close $f']
    (out/'sta.tcl').write_text('\n'.join(tcl)+'\n')
    (out/'upper-owners.tsv').write_bytes((flat/'expected-owners.tsv').read_bytes())
    (out/'constraints.json').write_text(json.dumps({'sources':audits,'sdc_sha256':sha(out/'input.sdc'),
        'netlist_sha256':sha(netlist),'boundary':'supplied independent resource clock/I/O constraints; no invented clock tree or gateway'},indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('base','binding','configs','flat','output'):p.add_argument(n,type=Path)
    a=p.parse_args();read=lambda p:json.loads(p.read_text());prepare(read(a.base),read(a.binding),read(a.configs),a.flat,a.output)
