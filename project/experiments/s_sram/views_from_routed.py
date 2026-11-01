"""Generate real LEF/model/timing views of an already routed, LVS-checked bank.

Does not reroute, replace geometry, or award DRC/timing qualification. Reads
actual GDS pins with OpenRAM's library-cell reader, verifies the reconstructed
transistor circuit, then runs real ngspice characterization in parallel with
the existing independent geometry checks. Internal wire PEX is unavailable.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
NAME='s_sram_256x128_freepdk45'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--routed-lvs',required=True,type=Path)
    ap.add_argument('--original-generation',required=True,type=Path)
    ap.add_argument('--out',required=True,type=Path)
    a=ap.parse_args();assert os.environ.get('SLURM_JOB_ID')
    out=a.out.resolve();out.mkdir(exist_ok=False,parents=True)
    record=dict(status='running',qualified=False,physical_acceptance=False,returncode=None,
                producer='views_from_routed',internal_wire_pex=False,commands=[],inputs={})
    def save():(out/'generation.json').write_text(json.dumps(record,indent=2)+'\n')
    def run(argv,name):
        argv=list(map(str,argv));start=time.monotonic()
        with (out/name).open('w') as f:p=subprocess.run(argv,cwd=out,stdout=f,stderr=subprocess.STDOUT)
        record['commands'].append(dict(argv=argv,returncode=p.returncode,seconds=time.monotonic()-start,log=name,sha256=sha(out/name)));save()
        assert p.returncode==0,(name,p.returncode)
    try:
        prior=a.routed_lvs.resolve();receipt=prior/'receipt.json'
        proof=json.loads(receipt.read_text());assert proof['passed'] and proof['explicit_match']
        assert not proof['implicit_supply_connections'] and not proof['explicit_mismatch']
        record['inputs'][str(receipt)]=sha(receipt)
        gds=prior/(NAME+'.gds');old_sp=prior/(NAME+'.sp')
        for p in (gds,old_sp):
            assert sha(p)==next(v['sha256'] for v in proof['inputs'].values() if v['copy']==str(p))
            record['inputs'][str(p)]=sha(p)
        record['original_geometry_verifier']=str(a.original_generation.resolve())
        bank=out/'bank';bank.mkdir()
        target=bank/gds.name;shutil.copyfile(gds,target);assert sha(target)==sha(gds)
        config=out/'run_config.py'
        config.write_text((HERE/'openram_config.py').read_text()+
            f'\noutput_path = {str(bank)!r}\nnetlist_only = True\nuse_pex = False\nperimeter_pins = False\n')
        record.update(config_sha256=sha(HERE/'openram_config.py'),run_config_sha256=sha(config));save()
        # Normal OpenRAM netlist construction. Geometry comes exclusively from
        # the checked actual GDS; no layout or verification option is waived.
        sys.argv=[sys.argv[0],str(config)]
        import openram
        from openram import OPTS
        openram.parse_args()
        OPTS.top_process='openram'
        openram.init_openram(config_file=str(config))
        openram.setup_bitcell()
        assert OPTS.netlist_only and OPTS.check_lvsdrc and not OPTS.analytical_delay and not OPTS.use_pex
        from openram import sram
        memory=sram(name=NAME)
        check_sp=out/'reconstructed-lvs.sp';memory.sp_write(str(check_sp),lvs=True)
        record['reconstructed_lvs_sp_sha256']=sha(check_sp)
        if sha(check_sp)==sha(old_sp):
            record['circuit_identity']='Byte-exact transistor LVS schematic matches existing actual-GDS LVS input'
        else:
            deck=prior/'freepdk45.lylvs';assert sha(deck)==next(v['sha256'] for v in proof['inputs'].values() if v['copy']==str(deck))
            run(['klayout','-b','-r',deck,'-rd','input='+str(target),'-rd','schematic='+str(check_sp),
                 '-rd','report='+str(out/'reconstructed.lvsdb'),'-rd','target_netlist='+str(out/'reconstructed-extracted.spice')],
                'reconstructed-lvs.log')
            text=(out/'reconstructed-lvs.log').read_text()
            assert text.count('CONGRATULATIONS! Netlists match.')==1 and 'ERROR' not in text
            record['circuit_identity']='Independent actual-GDS transistor LVS explicitly matches the reconstructed characterization circuit, without implicit supplies'
        save()
        from openram.base import utils
        from openram.tech import GDS,layer
        memory.s.width,memory.s.height=utils.get_gds_size(NAME,str(target),GDS['unit'],layer['boundary'])
        memory.s.pin_map=utils.get_gds_pins(list(memory.s.pins),NAME,str(target),GDS['unit'])
        assert len(memory.s.pin_map)==269 and all(memory.s.pin_map.values())
        record['gds_dimensions_um']=[memory.s.width,memory.s.height]
        record['actual_pin_shape_counts']={n:len(v) for n,v in memory.s.pin_map.items()}
        # Export only the existing geometry's abstraction. Restore netlist-only
        # before save(), which must never overwrite the copied routed GDS.
        OPTS.netlist_only=False
        try:memory.lef_write(str(bank/(NAME+'.lef')))
        finally:OPTS.netlist_only=True
        assert sha(target)==sha(gds);save()
        memory.save()  # Real ngspice tables and actual OpenRAM Verilog model.
        assert sha(target)==sha(gds)
        views={}
        for ext in ('v','lef','gds','sp','lib'):
            matches=list(bank.glob(NAME+('*' if ext=='lib' else '')+'.'+ext));assert len(matches)==1,(ext,matches)
            p=matches[0];views[ext]=dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)
        record.update(status='views_generated_not_qualified',returncode=0,views=views,
            scope='Actual LVS-checked routed GDS, actual-GDS pin/size LEF, LVS-verified transistor circuit, real ngspice schematic characterization and OpenRAM model. Full geometry DRC and complete S gates remain mandatory. No internal SRAM wire PEX or hard-macro qualification claimed.')
        save()
        openram.end_openram()
    except BaseException as e:
        record.update(status='view_assembly_failed',returncode=1,failure=repr(e));save();raise
    finally:save()

if __name__=='__main__':main()
