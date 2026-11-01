"""Fresh complete S implementation using actual generated SRAM views.

Pipeline completion is NOT qualification. Never accepts the simulation stand-in,
fake RAM views, another S physical database, or an uncharacterized bank receipt.
Execute inside an allocated ORFS container; outputs require independent gates.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
TOP = 'block_feed_s_macro_sram'
BANK = 's_sram_256x128_freepdk45'

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--generation',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    assert os.environ.get('SLURM_JOB_ID'), 'EDA requires an allocated job'
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    record=dict(passed=False,qualified=False,pipeline_completed=False,
                job_id=os.environ['SLURM_JOB_ID'],affinity=sorted(os.sched_getaffinity(0)),
                commands=[],inputs={},final_files={})
    def save():
        (out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
    def run(argv,log):
        argv=list(map(str,argv));start=time.time()
        with (out/log).open('w') as f:
            p=subprocess.run(argv,cwd=out,stdout=f,stderr=subprocess.STDOUT)
        record['commands'].append(dict(argv=argv,log=log,sha256=sha(out/log),
                                       returncode=p.returncode,seconds=time.time()-start))
        save()
        if p.returncode:raise RuntimeError((log,p.returncode))
    try:
        receipt=a.generation.resolve()/'generation.json'
        g=json.loads(receipt.read_text())
        assert g['status']=='views_generated_not_qualified' and g['returncode']==0
        record['inputs'][str(receipt)]=sha(receipt)
        views={k:Path(v['path']) for k,v in g['views'].items()}
        for k,p in views.items():
            assert sha(p)==g['views'][k]['sha256'];record['inputs'][str(p)]=sha(p)
        # The producer's checked config requires real ngspice characterization.
        config=(a.generation/'run_config.py').read_text()
        assert re.search(r'(?m)^analytical_delay\s*=\s*False\s*$',config)
        assert re.search(r'(?m)^check_lvsdrc\s*=\s*True\s*$',config)
        record['inputs'][str(a.generation/'run_config.py')]=sha(a.generation/'run_config.py')
        flow=Path('/OpenROAD-flow-scripts/flow');platform=flow/'platforms/nangate45'
        std=platform/'lib/NangateOpenCellLibrary_typical.lib'
        rtl=[ROOT/'project/rtl/s_sram/block_feed_s16k_sram.sv',
             ROOT/'project/rtl/s_sram/block_feed_s_macro_sram.sv',
             ROOT/'project/rtl/block_feed_v1/block_feed_loader.sv']
        for p in rtl+[std,platform/'lef/NangateOpenCellLibrary.tech.lef']:
            record['inputs'][str(p)]=sha(p)
        ys=f'read_liberty -lib {std}\nread_liberty -lib {views["lib"]}\n'
        ys+='read_verilog -sv '+' '.join(map(str,rtl))+'\n'
        ys+=f'hierarchy -check -top {TOP}\nsynth -top {TOP} -flatten\n'
        ys+=f'dfflibmap -liberty {std}\nabc -liberty {std}\nclean\ncheck -assert\n'
        ys+='write_json mapped.json\nwrite_verilog -noattr -noexpr -norename input.v\n'
        (out/'map.ys').write_text(ys);run(['yosys','-s',out/'map.ys'],'map.log')
        module=json.loads((out/'mapped.json').read_text())['modules'][TOP]
        banks=[n for n,c in module['cells'].items() if c['type']==BANK]
        assert len(banks)==4
        assert not any(c['type'].startswith('$') for c in module['cells'].values())
        lef=views['lef'].read_text()
        dimensions=re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;',lef)
        assert dimensions
        w,h=map(float,dimensions.groups())
        sys.path.insert(0,str(ROOT/'project/experiments/block_v1'))
        from pin_contract import script as pin_script
        from constraints import generate as constraints
        from native_reroute import config_suffix
        sys.path.insert(0,str(ROOT/'project/experiments/block_feed_v1'))
        from pins import generate
        technology=json.loads((ROOT/'project/experiments/block_v1/technology-2um-v1.json').read_text())
        ports={n:dict(bits=len(p['bits']),direction=p['direction'])for n,p in module['ports'].items()}
        side=math.ceil(max(400,2*w+180,2*h+180)/10)*10
        while True:
            try:plan,fixture,geometry=generate(ports,side,technology);break
            except AssertionError as e:
                if not e.args or not isinstance(e.args[0],tuple) or e.args[0][0]!='Insufficient staggered interface tracks':raise
                side+=10
        (out/'pins.json').write_text(json.dumps(plan,indent=2)+'\n')
        (out/'pins.tcl').write_text(pin_script(plan))
        (out/'interface-fixture.json').write_text(json.dumps(fixture,indent=2)+'\n')
        budget=json.loads((ROOT/'project/experiments/block_v1/physical-budget-300mhz.json').read_text())
        sdc=constraints(budget)
        sdc=re.sub(r'create_clock -name core -period [^ ]+',
                   'create_clock -name core -period %.15g'%budget['clock_ns'],sdc)
        (out/'input.sdc').write_text(sdc)
        placement='set block [ord::get_db_block]\nset banks {}\n'
        placement+=f'foreach inst [$block getInsts] {{if {{[[$inst getMaster] getName] eq "{BANK}"}} {{lappend banks [$inst getName]}}}}\n'
        placement+='if {[llength $banks]!=4} {error "Exactly four real SRAM instances required"}\n'
        placement+='set banks [lsort $banks]\n'
        for i in range(4):
            x=50+(i%2)*(w+40);y=50+(i//2)*(h+40)
            placement+=f'set inst [$block findInst [lindex $banks {i}]]\n'
            placement+=f'$inst setOrient R0\n$inst setLocation {round(x*2000)} {round(y*2000)}\n$inst setPlacementStatus LOCKED\n'
        (out/'macros.tcl').write_text(placement)
        grid=(platform/'grid_strategy-M1-M4-M7.tcl').read_text()
        grid='add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^vdd$} -power\n'+\
             'add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^gnd$} -ground\n'+grid
        (out/'pdn.tcl').write_text(grid)
        nickname='s_sram_155'
        cfg=f'export PLATFORM = nangate45\nexport DESIGN_NAME = {TOP}\nexport DESIGN_NICKNAME = {nickname}\n'
        for key,val in dict(VERILOG_FILES=out/'input.v',SDC_FILE=out/'input.sdc',
                            ADDITIONAL_LIBS=views['lib'],ADDITIONAL_LEFS=views['lef'],
                            ADDITIONAL_GDS=views['gds'],FOOTPRINT_TCL=out/'pins.tcl',
                            MACRO_PLACEMENT_TCL=out/'macros.tcl',PDN_TCL=out/'pdn.tcl').items():
            cfg+=f'export {key} = {val}\n'
        cfg+=f'export DIE_AREA = 0 0 {side} {side}\nexport CORE_AREA = 20 20 {side-20} {side-20}\n'
        cfg+='export PLACE_DENSITY = 0.45\nexport KEEP_VARS = 1\nexport LEC_CHECK = 1\nexport SEC_CHECK = 0\n'
        cfg+='override export MIN_ROUTING_LAYER = metal1\noverride export MAX_ROUTING_LAYER = metal10\n'
        cfg+='export GDS_ALLOW_EMPTY = ^__NO_EMPTY_CELLS_ALLOWED__$$\n'
        # Charge the same native input protection/repair resources as the
        # existing block flow; no relaxed timing or electrical acceptance.
        hook=(ROOT/'project/experiments/block_v1/native_input_diodes.tcl').read_text()
        hook=hook.replace('  if {[$port getName] eq "clk"} {continue}\n','')
        (out/'input-diodes.tcl').write_text(hook)
        cfg+=config_suffix(40,.005,out/'input-diodes.tcl','metal10')
        cfg+='export HOLD_SLACK_MARGIN = 0.02\n'
        (out/'config.mk').write_text(cfg)
        results=out/'flow/results/nangate45'/nickname/'base';results.mkdir(parents=True)
        for ext in ('v','sdc'):
            target=results/('1_2_yosys.'+ext);shutil.copyfile(out/('input.'+ext),target);target.chmod(0o444)
        record.update(bank_instances=banks,bank_dimensions_um=[w,h],die_um=[side,side],
                      budget=budget,config_sha256=sha(out/'config.mk'),stages=[],
                      scope='Complete fresh S route with real banks. Independent full merged-GDS DRC, STA/electrical/PG/pins, function and strict equivalence acceptance remain mandatory.')
        save()
        command=['make','-C',str(flow),'DESIGN_CONFIG='+str(out/'config.mk'),
                 'WORK_HOME='+str(out/'flow'),'NUM_CORES=16']
        for stage in ('do-1_synth','do-floorplan','do-place','do-cts','do-route','do-finish'):
            run(command+[stage],stage+'.log');record['stages'].append(stage);save()
        run(command+['do-gds'],'do-gds.log')
        record['stages'].append('do-gds');save()
        for ext in ('v','sdc','def','odb','spef','gds'):
            p=results/('6_final.'+ext);assert p.is_file()
            record['final_files'][p.name]=dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)
        run(command+['drc'],'whole-gds-drc.log')
        report=out/'flow/reports/nangate45'/nickname/'base/6_drc.lyrdb'
        tree=ET.parse(report)
        items=tree.findall('.//items/item')
        record['whole_gds_drc']=dict(path=str(report),sha256=sha(report),items=len(items),clean=not items)
        image_script='''import pya
view=pya.LayoutView()
view.load_layout(INPUT,0)
view.max_hier()
view.add_missing_layers()
view.zoom_fit()
view.save_image(OUTPUT,1600,1600)
'''.replace('INPUT',repr(str(results/'6_final.gds'))).replace('OUTPUT',repr(str(out/'layout.png')))
        (out/'render.py').write_text(image_script)
        run(['env','QT_QPA_PLATFORM=offscreen','klayout','-z','-r',out/'render.py'],'render.log')
        assert (out/'layout.png').stat().st_size>1000
        record['image']=dict(path=str(out/'layout.png'),sha256=sha(out/'layout.png'))
        record.update(passed=True,pipeline_completed=True)
    except Exception as e:
        record['failure']=repr(e)
        raise
    finally:
        save()

if __name__=='__main__':main()
