"""Independent native wirelength reporting from a sealed complete final ODB."""
import hashlib
import json
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
        observations[label]=dict(source=str(source),odb_sha256=digest(odb),
            source_manifest_sha256=hashlib.sha256((source/'output.sha256').read_bytes()).hexdigest(),
            native_drt_wire_um=metrics['detailedroute__route__wirelength'],
            native_drt_vias=metrics['detailedroute__route__vias'],
            report=log.name,report_sha256=digest(log),
            scope='Native report_wire_length -net * -detailed_route -summary on the complete sealed final ODB; independent of the DRT iteration table. No layout or source mutation.')
    (ROOT/'wire-audit-sources.json').write_text(json.dumps(observations,indent=2)+'\n')
