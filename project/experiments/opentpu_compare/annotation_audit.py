"""Classify every unannotated STA driver through native flat connectivity."""
import hashlib
import json
from pathlib import Path
import re


def execute(root,sources,run_tcl,track):
    results={}
    for label,folder in sources.items():
        source=Path(folder)
        manifest={name[2:]:h for h,name in (line.split(None,1) for line in (source/'output.sha256').read_text().splitlines())}
        for name in ['full-hierarchy-sta.tcl','full-hierarchy-sta.log','full-hierarchy-quality.json']:
            path=source/name
            assert hashlib.sha256(path.read_bytes()).hexdigest()==manifest[name]
            track(path)
        log=(source/'full-hierarchy-sta.log').read_text()
        match=re.search(r'Found (\d+) unannotated drivers\.\n(.*?)Found (\d+) partially unannotated drivers\.',log,re.S)
        assert match, 'Missing complete native annotation report'
        names=[line.strip() for line in match[2].splitlines() if line.strip()]
        assert len(names)==int(match[1])
        script=(source/'full-hierarchy-sta.tcl').read_text()
        for path in re.findall(r'read_(?:lef|liberty|verilog|sdc|spef)(?: -path \w+)? \{([^}]+)\}',script):track(Path(path))
        # Reload the same design and RC without duplicating its 40k-line list.
        script=script[:script.index('set_propagated_clock [all_clocks]')]
        script+='set_propagated_clock [all_clocks]\n'
        script+='set control [get_fanout -from [get_ports clk] -flat -pin_levels 2 -trace_arcs all]\n'
        script+='if {![llength $control]} {error {Fanout auditor failed its connected-clock positive control}}\n'
        def quoted(s):
            for a,b in [('\\','\\\\'),('"','\\"'),('$','\\$'),('[','\\['),(']','\\]')]:s=s.replace(a,b)
            return '"'+s+'"'
        output=root/(label+'-unannotated-connectivity.tsv')
        script+='set f [open {'+str(output)+'} w]\n'
        script+='set drivers [list '+' '.join(map(quoted,names))+']\n'
        script+='''foreach name $drivers {
  set pins [get_pins -quiet $name]
  if {![llength $pins]} {set pins [get_ports -quiet $name]}
  if {[llength $pins] != 1} {puts $f "$name\\tMISSING_OR_AMBIGUOUS";continue}
  set count 0
  set examples {}
  foreach reached [get_fanout -from $pins -flat -pin_levels 2 -trace_arcs all] {
    if {[lsearch -exact $pins $reached]>=0} {continue}
    incr count
    if {[llength $examples]<3} {lappend examples [get_full_name $reached]}
  }
  puts $f "$name\\t$count\\t$examples"
}
close $f
'''
        run_tcl('annotation-'+label,script)
        rows=[line.split('\t') for line in output.read_text().splitlines()]
        errors=[line for line in rows if line[1]!='0']
        checks=dict(all_reported_drivers_resolved=len(rows)==len(names),
            unannotated_drivers_have_no_connected_fanout=not errors,
            partial_driver_count_zero=int(match[3])==0,
            no_reported_unconstrained_endpoints='unconstrained endpoints' not in log.lower(),
            no_reported_missing_clocks='no clock' not in log.lower())
        results[label]=dict(passed=all(checks.values()),checks=checks,source=str(source),
            unannotated_unused_driver_count=len(names),partially_unannotated_driver_count=int(match[3]),
            first_errors=errors[:30],connectivity_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
            scope='Native flat get_fanout through all arcs, pin depth 2, for every unannotated driver; connected-clock positive control. Timing acceptance remains separate.')
    (root/'annotation-validation.json').write_text(json.dumps(results,indent=2)+'\n')
    assert all(row['passed'] for row in results.values()), 'Unannotated driver has unresolved or connected fanout'
