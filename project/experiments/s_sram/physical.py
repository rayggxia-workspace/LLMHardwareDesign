"""Fresh complete S implementation using actual generated SRAM views.

Pipeline completion is NOT qualification. Never accepts the simulation stand-in,
fake RAM views, another S physical database, or an uncharacterized bank receipt.
Execute inside an allocated ORFS container; outputs require independent gates.
"""
import argparse
import copy
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
    ap.add_argument('--hold-repair-margin',type=float,choices=[.02,.03],default=.03,
                    help='Physical hold repair target only; final timing constraints never change')
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
        normalize=Path(__file__).with_name('normalize_gds.py')
        record['inputs'][str(normalize)]=sha(normalize)
        normalized=out/'bank-stream.gds';normalization=out/'bank-stream.json'
        run(['klayout','-b','-r',normalize,'-rd','SOURCE='+str(views['gds']),
             '-rd','OUTPUT='+str(normalized),'-rd','RECEIPT='+str(normalization)],'bank-stream.log')
        nr=json.loads(normalization.read_text());assert nr['passed'] and nr['all_cell_masks_labels_and_instances_exact']
        record['bank_stream_normalization']=dict(path=str(normalization),sha256=sha(normalization))
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
        ys+='write_json mapped.json\n'
        (out/'map.ys').write_text(ys);run(['yosys','-s',out/'map.ys'],'map.log')
        sys.path.insert(0,str(ROOT/'project/experiments/block_v1'))
        from structural_view import unsigned, compare
        mapped=json.loads((out/'mapped.json').read_text())
        removed=[]
        for m in mapped['modules'].values():
            for name,cell in list(m.get('cells',{}).items()):
                if cell['type']=='$scopeinfo':
                    assert not cell['connections'];removed.append(name);del m['cells'][name]
                else:assert not cell['type'].startswith('$'),cell['type']
        has_signed=any(v.get('signed') for m in mapped['modules'].values()
                       for k in ('ports','netnames') for v in m.get(k,{}).values())
        metadata=unsigned(mapped) if has_signed else dict(removed_signed_metadata=[])
        metadata['removed_portless_scope_annotations']=removed
        (out/'unsigned.json').write_text(json.dumps(mapped)+'\n')
        script=f'read_json {out/"unsigned.json"}\nhierarchy -check -top {TOP}\n'
        script+='write_verilog -noattr -noexpr -norename input.v\nwrite_json structural.json\n'
        script+=f'design -reset\nread_liberty -lib {std}\nread_liberty -lib {views["lib"]}\n'
        script+=f'read_verilog input.v\nhierarchy -check -top {TOP}\nwrite_json reparsed.json\n'
        (out/'structural.ys').write_text(script)
        run(['yosys','-s',out/'structural.ys'],'structural.log')
        expected=json.loads((out/'structural.json').read_text())
        observed=json.loads((out/'reparsed.json').read_text())
        proof=compare(expected,observed);negative=copy.deepcopy(observed)
        cell=next(iter(negative['modules'][TOP]['cells'].values()))
        bits=next(v for v in cell['connections'].values() if v)
        bits[0]='1' if bits[0]!='1' else '0'
        rejected=False
        try:compare(expected,negative)
        except AssertionError:rejected=True
        assert rejected
        proof.update(metadata=metadata,single_pin_bit_negative_rejected=True)
        (out/'structural-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
        record['structural_proof']=dict(path=str(out/'structural-proof.json'),
                                        sha256=sha(out/'structural-proof.json'))
        module=mapped['modules'][TOP]
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
                              ADDITIONAL_GDS=normalized,FOOTPRINT_TCL=out/'pins.tcl',
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
        bank_hook=Path(__file__).with_name('bank_buffers.tcl')
        record['inputs'][str(bank_hook)]=sha(bank_hook)
        # Build the functional delay/boundary resources before the protection
        # hook seals input root nets. The original protection checks and
        # dont_touch guards then apply to the finished topology unchanged.
        hook=bank_hook.read_text()+'\n'+hook
        (out/'input-diodes.tcl').write_text(hook)
        cfg+=config_suffix(40,.005,out/'input-diodes.tcl','metal10')
        cfg+=f'export HOLD_SLACK_MARGIN = {a.hold_repair_margin}\n'
        record['repair_targets']=dict(hold_margin_ns=a.hold_repair_margin,cap_margin_percent=40,
             bank_output_receiver='CLKBUF_X1',bank_receiver_drop_um=1.4,
             local_bank_output_topology_fixed=True,acceptance_constraints_unchanged=True)
        # Keep actual technology endcaps; filler cells are not substitutes.
        # Four-micron row halo is a placement setting, not a well-rule waiver.
        # Actual bank well masks have independently been checked inside LEF.
        tapcell=out/'tapcell.tcl'
        tapcell.write_text('tapcell -distance 120 -tapcell_master "$::env(TAP_CELL_NAME)" -endcap_master "$::env(TAP_CELL_NAME)" -halo_width_x 4 -halo_width_y 4 -disallow_one_site_gaps\n')
        cfg+='export TAPCELL_TCL = '+str(tapcell)+'\n'
        patch_generator=Path(__file__).with_name('landing_patches.py')
        patch_hook=Path(__file__).with_name('landing_patches.tcl')
        for source in [patch_generator,patch_hook]:record['inputs'][str(source)]=sha(source)
        patch_data=out/'landing-patches-data.tcl';patch_proof=out/'landing-patches.json'
        run(['klayout','-b','-r',patch_generator,'-rd','GDS='+str(views['gds']),
             '-rd','LEF='+str(views['lef']),'-rd','OUTPUT='+str(patch_data),
             '-rd','RECEIPT='+str(patch_proof)],'landing-patches.log')
        patch_result=json.loads(patch_proof.read_text());assert patch_result['passed']
        # DRT must see the complete future landing footprint before routing,
        # otherwise a legal pre-patch wire can be 65nm from the added metal.
        # The original matched five bank views remain unchanged. This access
        # view is valid only with the priced top-level ODB patches below.
        cfg+='export ADDITIONAL_LEFS = '+patch_result['routing_lef']['path']+'\n'
        access_script=out/'landing-access.tcl';access_tsv=out/'landing-access.tsv'
        access_script.write_text(f'''read_lef {{{platform/'lef/NangateOpenCellLibrary.tech.lef'}}}
read_lef {{{patch_result['routing_lef']['path']}}}
set master [[ord::get_db] findMaster {BANK}]
set stream [open {{{access_tsv}}} w]
foreach term [$master getMTerms] {{
  if {{[$term getName] in {{vdd gnd}}}} {{continue}}
  foreach pin [$term getMPins] {{
    foreach box [$pin getGeometry] {{
      if {{[[$box getTechLayer] getName] ne "metal3"}} {{continue}}
      puts $stream "[$term getName]\\t[$box xMin]\\t[$box yMin]\\t[$box xMax]\\t[$box yMax]"
    }}
  }}
}}
close $stream
''')
        run(['openroad','-exit',access_script],'landing-access.log')
        actual_access={}
        for line in access_tsv.read_text().splitlines():
            name,*values=line.split('\t');assert name not in actual_access
            actual_access[name]=list(map(int,values))
        assert actual_access=={p['pin']:p['rect_dbu']for p in patch_result['patches']}
        record['landing_access_readback']=dict(passed=True,path=str(access_tsv),sha256=sha(access_tsv),
              script_path=str(access_script),script_sha256=sha(access_script),pins=len(actual_access))
        hook=out/'landing-patches.tcl';hook.write_text(patch_data.read_text()+patch_hook.read_text())
        cfg+='export POST_DETAIL_ROUTE_TCL = '+str(hook)+'\n'
        record['landing_patches']=dict(path=str(patch_proof),sha256=sha(patch_proof))
        # All imported GDS and DEF reader options share 100pm resolution.
        # The native ODB/DEF remains 2000 DBU/um; physical-unit readback below
        # independently checks conversions rather than assuming equal DBUs.
        template=platform/'FreePDK45.lyt'
        record['inputs'][str(template)]=sha(template)
        technology_tree=ET.parse(template)
        for node in technology_tree.findall('.//dbu'):node.text='0.0001'
        private_tech=out/'FreePDK45.lyt'
        technology_tree.write(private_tech,encoding='utf-8',xml_declaration=True)
        cfg+='override export KLAYOUT_TECH_FILE = '+str(private_tech)+'\n'
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
        # Preserve the native stream and verify a mask-identical well-union
        # representation before hashing the actual final GDS and full DRC.
        well_script=Path(__file__).with_name('coalesce_wells.py')
        record['inputs'][str(well_script)]=sha(well_script)
        raw_stream=results/'6_stream_raw.gds';(results/'6_final.gds').rename(raw_stream)
        well_proof=out/'well-stream.json'
        run(['klayout','-b','-r',well_script,'-rd','SOURCE='+str(raw_stream),
             '-rd','OUTPUT='+str(results/'6_final.gds'),'-rd','RECEIPT='+str(well_proof)],'well-stream.log')
        assert json.loads(well_proof.read_text())['passed']
        record['well_stream']=dict(path=str(well_proof),sha256=sha(well_proof))
        for ext in ('v','sdc','def','odb','spef','gds'):
            p=results/('6_final.'+ext);assert p.is_file()
            record['final_files'][p.name]=dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)
        stream_check=Path(__file__).with_name('stream_geometry.py')
        record['inputs'][str(stream_check)]=sha(stream_check)
        inventory_script=Path(__file__).with_name('stream_inventory.tcl')
        record['inputs'][str(inventory_script)]=sha(inventory_script)
        inventory=out/'stream-native.tsv'
        run(['env','SRAM_STREAM_ODB='+str(results/'6_final.odb'),
             'SRAM_STREAM_INVENTORY='+str(inventory),'openroad','-exit',inventory_script],
            'stream-native.log')
        stream_proof=out/'stream-geometry.json'
        run(['klayout','-b','-r',stream_check,'-rd','DEFINITION='+str(results/'6_final.def'),
             '-rd','GDS='+str(results/'6_final.gds'),'-rd','BANK_GDS='+str(views['gds']),
             '-rd','NATIVE_INVENTORY='+str(inventory),'-rd','ODB='+str(results/'6_final.odb'),
             '-rd','RECEIPT='+str(stream_proof)],'stream-geometry.log')
        assert json.loads(stream_proof.read_text())['passed']
        record['stream_geometry']=dict(passed=True,path=str(stream_proof),sha256=sha(stream_proof))
        report=out/'flow/reports/nangate45'/nickname/'base/6_drc.lyrdb'
        # Run the unchanged full deck on the immutable merged GDS. A make
        # aggregate target can revisit Yosys dependencies and try to replace
        # the intentionally protected, structurally checked input netlist.
        deck=platform/'drc/FreePDK45.lydrc'
        record['inputs'][str(deck)]=sha(deck)
        gds_sha=sha(results/'6_final.gds')
        run(['klayout','-b','-r',deck,'-rd','in_gds='+str(results/'6_final.gds'),
             '-rd','report_file='+str(report)],'whole-gds-drc.log')
        assert sha(results/'6_final.gds')==gds_sha
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
