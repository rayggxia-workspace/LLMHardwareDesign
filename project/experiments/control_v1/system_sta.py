"""Complete native-cell/SPEF hierarchical timing diagnostic at 300 MHz.

Without upper parasitics this is an explicitly optimistic diagnostic, never
physical acceptance. It finds boundary failures before expensive mask assembly.
"""
import argparse,hashlib,json,os,subprocess,sys,socket,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--topology',type=Path,required=True)
    p.add_argument('--graph',type=Path,required=True);p.add_argument('--functional-views',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--stitch-native-access',action='store_true')
    p.add_argument('--reuse-native-stitch',type=Path)
    p.add_argument('--audit-native-coverage',action='store_true')
    p.add_argument('--upper-geometry',type=Path)
    p.add_argument('--rc-variant',choices=['low','base','high'],default='base');a=p.parse_args()
    assert not a.reuse_native_stitch or a.stitch_native_access
    assert not a.audit_native_coverage or a.stitch_native_access
    assert not a.upper_geometry or (a.stitch_native_access and a.audit_native_coverage and not a.reuse_native_stitch)
    assert os.environ.get('SLURM_JOB_ID') and len(os.sched_getaffinity(0))<=16
    a.out.mkdir(parents=True,exist_ok=False)
    memory={k:int(v.split()[0])*1024 for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())}
    admission=dict(host=socket.gethostname(),available_bytes=memory['MemAvailable'],compile_forecast_gib=128,sta_forecast_gib=96,headroom=1.2,guard_gib=16)
    (a.out/'memory-admission.json').write_text(json.dumps(admission,indent=2)+'\n')
    assert memory['MemAvailable']>((128+96)*1.2+16)*1024**3
    receipt=dict(passed=False,execution_passed=False,job=os.environ['SLURM_JOB_ID'],inputs={},whole_system_qualified=False,
                 scope='Optimistic zero-upper-RC timing diagnostic. All actual final native cells and native SPEF retained. Not physical acceptance.')
    def bind(path,digest=None):
        actual=sha(path)
        if digest:assert actual==digest,path
        receipt['inputs'][str(path)]=actual
    try:
        m=json.loads(a.manifest.read_text());g=json.loads(a.graph.read_text());t=json.loads(a.topology.read_text())['modules']['control_system']
        bind(a.manifest);bind(a.graph);bind(a.topology);bind(a.functional_views);bind(Path(__file__))
        views=json.loads(a.functional_views.read_text())['leaves']
        view_keys={top:row.get('bundle',{}).get('macro',top) for top,row in m['leaves'].items()}
        assert set(views)==set(view_keys.values())
        from boundary_links import validate
        bind(Path(__file__).with_name('boundary_links.py'));validate(m,g)
        assert g['instances'].get('reset_distribution')=='control_reset_distribution'
        assert {n:c['type'] for n,c in t['cells'].items()}==g['instances']
        # Independently check every connected bit and direction against the
        # graph already checked for hidden active glue and physical pin names.
        ends={}
        for name,cell in t['cells'].items():
            plan=Path(m['leaves'][cell['type']]['pins']);bind(plan,m['leaves'][cell['type']]['pins_sha256'])
            pins={p['pin'] for p in json.loads(plan.read_text())['pins']}
            for port,bits in cell['connections'].items():
                for index,bit in enumerate(bits):
                    assert isinstance(bit,int)
                    pin=port+'['+str(index)+']' if port+'['+str(index)+']' in pins else port
                    assert pin in pins
                    ends.setdefault(str(bit),[]).append(dict(instance=name,pin=pin,direction=cell['port_directions'][port]))
        for port,row in t['ports'].items():
            for index,bit in enumerate(row['bits']):
                assert isinstance(bit,int)
                ends.setdefault(str(bit),[]).append(dict(instance='TOP',pin=port+('['+str(index)+']' if len(row['bits'])>1 else ''),direction='output' if row['direction']=='input' else 'input'))
        for bit,c in g['connections'].items():
            key=lambda e:(e['instance'],e['pin'],e['direction'])
            assert sorted(map(key,ends[bit]))==sorted(map(key,[c['driver'],*c['sinks']]))
        text=['module control_system('+','.join(t['ports'])+');']
        for name,row in t['ports'].items():
            text.append(row['direction']+' '+('['+str(len(row['bits'])-1)+':0] ' if len(row['bits'])>1 else '')+name+';')
        bits=sorted({b for row in t['ports'].values() for b in row['bits']}|{b for c in t['cells'].values() for bs in c['connections'].values() for b in bs})
        for bit in bits:text.append('wire net_'+str(bit)+';')
        for name,row in t['ports'].items():
            for index,bit in enumerate(row['bits']):
                pin=name+('['+str(index)+']' if len(row['bits'])>1 else '');net='net_'+str(bit)
                text.append('assign '+(net+' = '+pin if row['direction']=='input' else pin+' = '+net)+';')
        for name,cell in t['cells'].items():
            ports=[]
            for port,bits in cell['connections'].items():
                ports.append('.'+port+'('+('net_'+str(bits[0]) if len(bits)==1 else '{'+','.join('net_'+str(b) for b in reversed(bits))+'}')+')')
            text.append(cell['type']+' '+name+'('+','.join(ports)+');')
        text.append('endmodule');(a.out/'combined.v').write_text('\n'.join(text)+'\n')
        platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45');lib=platform/'lib/NangateOpenCellLibrary_typical.lib';bind(lib)
        script='set_thread_count 16\nread_liberty {'+str(lib)+'}\n'
        for name in ('NangateOpenCellLibrary.tech.lef','NangateOpenCellLibrary.macro.mod.lef'):
            path=platform/'lef'/name;bind(path);script+='read_lef {'+str(path)+'}\n'
        for top,row in m['leaves'].items():
            entry=row['final_files']['6_final.v'];bind(entry['path'],entry['sha256'])
            # write_verilog can omit physical input diodes. Use the already
            # qualified complete ODB-derived view, including every such cell.
            proof=views[view_keys[top]];bind(proof['receipt'],proof['receipt_sha256']);bind(proof['report'],proof['report_sha256'])
            gate=json.loads(Path(proof['receipt']).read_text());assert gate['passed'] and gate['outputs'][Path(proof['report']).name]==proof['report_sha256']
            report=json.loads(Path(proof['report']).read_text());assert report['passed']
            view=report['full_final_netlist'];assert view['passed']
            bind(view['full_view'],view['full_view_sha256'])
            for path,digest in view['input_sha256'].items():bind(path,digest)
            physical_inputs={Path(path).name:digest for path,digest in view['input_sha256'].items()}
            assert len(physical_inputs)==len(view['input_sha256'])==2
            assert physical_inputs['6_final.v']==entry['sha256']
            odb=row['final_files']['6_final.odb'];assert physical_inputs['6_final.odb']==odb['sha256']
            assert 'wire signed' not in Path(view['full_view']).read_text(),top
            script+='read_verilog {'+view['full_view']+'}\n'
        script+='read_verilog {'+str(a.out/'combined.v')+'}\nlink_design -hier control_system\n'
        script+='set names [open root-net-names.tsv w]\nset linked_root_names {}\nforeach net [get_nets -quiet *] {set name [get_full_name $net];lappend linked_root_names $name;puts $names $name}\nclose $names\n'
        if a.stitch_native_access:
            for bit,row in g['connections'].items():
                name=row['driver']['pin'] if row['driver']['instance']=='TOP' else 'net_'+bit
                script+='if {[lsearch -exact $linked_root_names {'+name+'}]<0} {error {Missing actual linked boundary root '+name+'}}\n'
        entry=m['leaves']['control_c']['final_files']['6_final.sdc'];bind(entry['path'],entry['sha256'])
        (a.out/'combined.sdc').write_bytes(Path(entry['path']).read_bytes());script+='read_sdc {'+str(a.out/'combined.sdc')+'}\n'
        for name,top in g['instances'].items():
            entry=m['leaves'][top]['final_files']['6_final.spef'];bind(entry['path'],entry['sha256'])
            if not a.stitch_native_access:script+='read_spef -path {'+name+'} {'+entry['path']+'}\n'
        if a.stitch_native_access:
            from native_stitch import stitch,reheader
            bind(Path(__file__).with_name('native_stitch.py'))
            if a.reuse_native_stitch:
                spef,proof=reheader(m,g,a.reuse_native_stitch,a.out,a.manifest,a.graph)
                bind(a.reuse_native_stitch/'receipt.json');bind(a.reuse_native_stitch/'native-stitch.json')
            else:
                upper=None
                if a.upper_geometry:
                    from upper_rc_network import UpperRC
                    upper=UpperRC(a.upper_geometry,g,m,a.rc_variant,bind)
                spef,proof=stitch(m,g,a.out,upper=upper)
            bind(spef,proof['output_sha256']);script+='read_spef {'+str(spef)+'}\n'
            receipt['native_access_stitched']=True
            if a.upper_geometry:
                receipt.update(actual_upper_distributed_research_rc=True,rc_variant=a.rc_variant,
                    scope='Actual read-back M11/M12 geometry distributed RC joined to every complete native SPEF under the declared research model. Whole physical/function/PG qualification remains separate; no manufacturing calibration claimed.')
        script+='set_propagated_clock [all_clocks]\nsta::find_timing\n'
        script+='report_checks -path_delay max -group_path_count 1 -digits 9 -format full_clock_expanded > critical-first.rpt\n'
        native=ROOT/'project/experiments/block_v1';tail=native/'native_sta.tcl';bind(tail);bind(native/'native_annotation.tcl')
        body=tail.read_text().split('sta::find_timing\n',1)[1]
        if a.audit_native_coverage:
            # Some physical no-arc inputs are omitted by sta::endpoints in
            # hierarchy. Explicitly add every such actual linked input and
            # query its real slacks/fanout under the same complete RC/SDC.
            # Keep all original endpoints. The existing strict type receiver
            # still requires each actual ODB protection sink exactly once.
            extra='''set complete_endpoints [sta::endpoints]
set endpoint_names {}
foreach pin $complete_endpoints {dict set endpoint_names [get_full_name $pin] 1}
set physical [open linked-passive.tsv w]
foreach cell [get_cells -hierarchical -filter {ref_name == ANTENNA_X1} *] {
  set name [get_full_name $cell]
  set pins [get_pins -quiet ${name}/A]
  if {[llength $pins]!=1} {error "Missing actual linked protection pin"}
  set pin [lindex $pins 0]
  set name [get_full_name $pin]
  set added [expr {![dict exists $endpoint_names $name]}]
  puts $physical "$name\\t[get_property $cell ref_name]\\t[string tolower [get_property $pin direction]]\\t$added"
  if {$added} {lappend complete_endpoints $pin;dict set endpoint_names $name 1}
}
close $physical
'''
            body=body.replace('set stream [open endpoints.tsv w]',extra+'set stream [open endpoints.tsv w]',1)
            body=body.replace('foreach pin [sta::endpoints] {','foreach pin $complete_endpoints {',1)
        # This diagnostic intentionally lacks top RC. Preserve the complete
        # partial-load report instead of sending it to the strict leaf-only
        # receiver, which correctly rejects partial connected annotations.
        # Full composition acceptance must independently reject those opens.
        body=body.replace('source [file join [file dirname [info script]] native_annotation.tcl]',
                          'source {'+str(native/'native_annotation.tcl')+'}' if a.audit_native_coverage else
                          '# Incomplete upper parasitics retained as diagnostic evidence; no acceptance granted.')
        script+=body;(a.out/'timing.tcl').write_text(script)
        with (a.out/'sta.log').open('w') as log:q=subprocess.run(['openroad','-no_init','-exit',a.out/'timing.tcl'],stdout=log,stderr=subprocess.STDOUT,cwd=a.out)
        assert q.returncode==0,'sta.log'
        sys.path.insert(0,str(native));from native_sta import inspect
        result=inspect(a.out);(a.out/'native-timing.json').write_text(json.dumps(result,indent=2)+'\n')
        annotations=(a.out/'annotation.rpt').read_text()
        counts=re.findall(r'^Found (\d+) (unannotated|partially unannotated) drivers\.$',annotations,re.M)
        assert len(counts)==2
        receipt.update(execution_passed=True,baseline_timing_passed=result['passed'],minimum_setup_ns=result['minimum_setup_ns'],minimum_hold_ns=result['minimum_hold_ns'],
                       incomplete_annotation_counts={kind:int(count) for count,kind in counts},full_annotation_accepted=False)
        if a.audit_native_coverage:
            from system_native_audit import audit
            bind(Path(__file__).with_name('system_native_audit.py'))
            proof=audit(m,g,a.out,lib,bind)
            receipt.update(native_coverage_audit_passed=proof['coverage']['passed'],
                           typed_native_timing_passed=proof['typed']['passed'])
            if a.upper_geometry:
                receipt['research_composed_timing_passed']=proof['passed']
    finally:
        receipt['outputs']={p.name:sha(p) for p in a.out.iterdir() if p.is_file()}
        (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')

if __name__=='__main__':main()
