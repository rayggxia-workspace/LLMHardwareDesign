"""Independent native wirelength reporting from a sealed complete final ODB."""
import hashlib
import json
import math
from pathlib import Path
import re
from run import ROOT, track, digest, run_tcl


def execute(sources):
    observations={}
    for label,path in sources.items():
        assert re.fullmatch(r'[a-z0-9_]+',label)
        source=Path(path)
        assert (source/'exit-code.txt').is_file()
        manifest={name[2:]:h for h,name in
                  (line.split(None,1) for line in (source/'output.sha256').read_text().splitlines())}
        def sealed(relative):
            f=source/relative
            assert digest(f)==manifest[str(relative)], 'Changed wire audit input: '+str(f)
            return track(f)
        meta=json.loads(sealed('experiment.json').read_text())
        relative=Path(meta['result_relative'])
        odb=sealed(relative/'6_final.odb')
        metrics_path=Path(str(relative).replace('/results/','/logs/'))/'5_2_route.json'
        metrics=json.loads(sealed(metrics_path).read_text())
        script='read_db {'+str(odb)+'}\nhelp report_wire_length\n'
        script+='report_wire_length -net * -detailed_route -summary\n'
        script+='set wires 0\nforeach net [[ord::get_db_block] getNets] {if {[$net getSigType] ni {POWER GROUND} && [$net getWire] ne "NULL"} {incr wires}}\n'
        script+='puts "FINAL_SIGNAL_WIRED_NET_COUNT $wires"\n'
        run_tcl('native-wire-'+label,script)
        log=ROOT/('native-wire-'+label+'.log')
        text=log.read_text()
        layers={layer:float(value) for layer,value in
                re.findall(r'^\s*(metal\d+)\s+([\d.]+)um\s+\d+%\s*$',text,re.M)}
        count=re.search(r'^FINAL_SIGNAL_WIRED_NET_COUNT (\d+)$',text,re.M)
        total=sum(layers.values())
        drt=metrics['detailedroute__route__wirelength']
        checks=dict(positive_finite_complete_odb_length=bool(layers) and math.isfinite(total) and total>0,
            wired_signal_nets_present=bool(count) and int(count[1])>0,
            independent_native_totals_within_one_percent=abs(total-drt)<=.01*drt)
        reuse=None
        if (source/'route-reuse.json').exists():
            reuse=json.loads(sealed(Path('route-reuse.json')).read_text())
            checks['all_retained_and_rerouted_signal_nets_present']=bool(count) and int(count[1])==(
                reuse['retained_incoming_regular_wires']+reuse['cleared_regular_wires'])
        observations[label]=dict(source=str(source),odb_sha256=digest(odb),
            source_manifest_sha256=hashlib.sha256((source/'output.sha256').read_bytes()).hexdigest(),
            native_drt_wire_um=metrics['detailedroute__route__wirelength'],
            native_drt_vias=metrics['detailedroute__route__vias'],
            odb_signal_wire_um=total,odb_signal_wire_by_layer_um=layers,
            drt_minus_odb_wire_um=drt-total,
            final_signal_wired_net_count=int(count[1]) if count else None,
            checks=checks,passed=all(checks.values()),
            report=log.name,report_sha256=digest(log),
            scope='Native report_wire_length -net * -detailed_route -summary on the complete sealed final ODB. DRT table remains the primary cost definition. The two native totals can differ; their observed difference is retained, with a 1% gross inconsistency check. No layout or source mutation.')
    (ROOT/'wire-audit-sources.json').write_text(json.dumps(observations,indent=2)+'\n')
    assert all(row['passed'] for row in observations.values()), 'Complete ODB wirelength crosscheck failed'
