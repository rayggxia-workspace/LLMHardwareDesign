"""Server-only stage2 runner: isolated links, real P group, optional mapped area."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import time

from check_logs import check
from render_group import render

HERE=Path(__file__).resolve().parent
VERILATOR=Path('/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator')
BANK=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v')
BANK_SHA='6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7'
LIBERTY=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
SEEDS=((1,143),(2,143),(2,144))
P_PASS='PASS P16 feed, two K segments, writeback, invalid command, gated SiLU and direct equivalence'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def expand_paths(text):
    out=[]
    for token in shlex.split(text):
        match=re.fullmatch(r'([^{}]*)\{([^{}]+)\}([^{}]*)',token)
        if match:out += [match[1]+name+match[3] for name in match[2].split(',')]
        elif '{' in token or '}' in token:raise ValueError('unsupported source expansion '+token)
        else:out.append(token)
    return out


def smoke_sources(repo):
    path=repo/'project/experiments/pu_leaf_base/smoke.sh'
    text=path.read_text(encoding='utf-8')
    common=re.search(r'common=\((.*?)\)\s*bank=',text,re.S)
    group=re.search(r'2\) top=tb_pu_p_group\s*src=\((.*?)\);;',text,re.S)
    if not common or not group:raise ValueError('frozen smoke.sh source anchors changed')
    sources=expand_paths(common[1])+expand_paths(group[1])
    required={'project/rtl/pu_leaf_base/pu_p_group.sv','project/rtl/pu_leaf_base/pj_feed_hold.sv'}
    if not required.issubset(sources) or len(sources)!=12:raise ValueError('unexpected P smoke source list '+str(sources))
    # Trace literal includes without executing anything from the repository.
    headers=set()
    for name in sources:
        for header in re.findall(r'`include\s+"([^"]+)"',(repo/name).read_text(encoding='utf-8')):
            resolved=repo/'project/rtl/block_v2'/header
            if not resolved.is_file():raise ValueError('missing included header '+str(resolved))
            headers.add(str(resolved.relative_to(repo)))
    return sources,sorted(headers),path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--repo',type=Path,default=HERE.parents[3])
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--stage1-result',type=Path,required=True)
    parser.add_argument('--deployment',type=Path)
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--yosys',type=Path)
    parser.add_argument('--liberty',type=Path,default=LIBERTY)
    a=parser.parse_args();a.repo=a.repo.resolve();a.out=a.out.resolve()
    a.out.mkdir(parents=True,exist_ok=False)
    report=dict(passed=False,scope='stage2 finite feeder RTL; no whole-model token/s, P&R or STA qualification',
                versions={'python':platform.python_version()},commands=[])

    def execute(command,log,allow_failure=False):
        command=list(map(str,command));start=time.monotonic()
        p=subprocess.run(command,cwd=a.out,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        log.write_bytes(p.stdout)
        record=dict(command=command,exit_code=p.returncode,elapsed_wall_seconds=time.monotonic()-start,
                    log=str(log.relative_to(a.out)),log_sha256=sha(log))
        report['commands'].append(record)
        if p.returncode and not allow_failure:raise RuntimeError('command failed '+str(command)+' '+p.stdout.decode(errors='replace')[-3000:])
        return record,p.stdout.decode(errors='replace')

    try:
        if not 1<=a.workers<=int(os.environ.get('SLURM_CPUS_PER_TASK','0')):raise ValueError('Slurm CPU allocation required')
        stage1=json.loads(a.stage1_result.read_text(encoding='utf-8'))
        if stage1.get('passed') is not True:raise ValueError('stage1 has not passed; stage2 prohibited')
        report['stage1_prerequisite']=dict(path=str(a.stage1_result),sha256=sha(a.stage1_result),passed=True)
        deployment=a.deployment or a.out.parent/'inputs.json'
        provenance=json.loads(deployment.read_text(encoding='utf-8')) if deployment.is_file() else {}
        report['source_commit']=provenance.get('source_commit','待核实')
        report['deployment_inputs_sha256']=sha(deployment) if deployment.is_file() else '待核实'
        if sha(BANK)!=BANK_SHA:raise ValueError('real SRAM bank identity drift')
        report['bank']=dict(path=str(BANK),sha256=BANK_SHA)
        sources,headers,smoke=smoke_sources(a.repo)
        report['upstream_inputs_sha256']={name:sha(a.repo/name) for name in sources+headers}
        report['upstream_inputs_sha256']['project/experiments/pu_leaf_base/smoke.sh']=sha(smoke)
        report['study_source_sha256']={p.name:sha(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.suffix in ('.sv','.py','.sh')}
        report['verilator_binary_sha256']=sha(VERILATOR)
        _,version=execute([VERILATOR,'--version'],a.out/'verilator-version.log')
        report['versions']['verilator']=version.strip()
        execute(['g++','--version'],a.out/'gcc-version.log')
        report['versions']['gcc']=(a.out/'gcc-version.log').read_text().splitlines()[0]
        staged=a.out/'staged';report['fork']=render(a.repo,staged)

        # Strict isolated new bench: deliberately no -Wno-fatal here.
        link_obj=a.out/'obj-link'
        common_flags=['--binary','--timing','--assert','--timescale','1ns/1ps',
                      '--x-initial','unique','--x-assign','unique','-j',str(a.workers)]
        execute([VERILATOR,*common_flags,'--top-module','bench_compare','--Mdir',link_obj,
                 staged/'baseline/pj_feed_hold.sv',HERE/'pj_feed_elastic.sv',HERE/'bench_compare.sv'],a.out/'link-build.log')
        negative,_=execute([link_obj/'Vbench_compare','+NEGATIVE_READY_EMPTY'],a.out/'link-negative.log',allow_failure=True)
        link=[]
        for mode,seed in SEEDS:
            log=a.out/f'link-positive-{mode}-{seed}.log'
            execute([link_obj/'Vbench_compare',f'+verilator+rand+reset+{mode}',f'+verilator+seed+{seed}'],log)
            link.append(dict(reset_mode=mode,seed=seed,checks=check(log,a.out/'link-negative.log',negative['exit_code'])))
        report['link']=link

        # P group uses exactly the original common/slot2 source selection.
        # Legacy RTL warnings retain the original smoke.sh -Wno-fatal setting;
        # the same new elastic module was already built strictly above.
        shared=[a.repo/name for name in sources if name not in (
            'project/rtl/pu_leaf_base/pu_p_group.sv','project/rtl/pu_leaf_base/pj_feed_hold.sv')]
        groups=[]
        for variant in ('baseline','candidate'):
            obj=a.out/('obj-p-'+variant)
            variant_files=[staged/variant/'pu_p_group.sv',staged/variant/('pj_feed_hold.sv' if variant=='baseline' else 'pj_feed_elastic.sv')]
            execute([VERILATOR,*common_flags,'-Wno-fatal','-I'+str(a.repo/'project/rtl/block_v2'),
                     '--top-module','tb_pu_p_group','--Mdir',obj,staged/'tb_pu_p_group_timed.sv',
                     *shared,*variant_files,BANK],a.out/(variant+'-p-build.log'))
            for mode,seed in SEEDS:
                log=a.out/f'p-{variant}-{mode}-{seed}.log'
                receipt,text=execute([obj/'Vtb_pu_p_group',f'+verilator+rand+reset+{mode}',f'+verilator+seed+{seed}'],log)
                cycles=re.findall(r'^P_GROUP_CYCLES (\d+)$',text,re.M)
                if P_PASS not in text or len(cycles)!=1:raise ValueError('missing P functional/cycle receipt '+str(log))
                groups.append(dict(variant=variant,reset_mode=mode,seed=seed,cycles=int(cycles[0]),
                                   original_functional_pass=True,log=receipt['log'],log_sha256=receipt['log_sha256']))
        report['P_group']=groups
        report['P_cycle_comparisons']=[]
        for mode,seed in SEEDS:
            old=next(r for r in groups if r['variant']=='baseline' and r['reset_mode']==mode and r['seed']==seed)
            new=next(r for r in groups if r['variant']=='candidate' and r['reset_mode']==mode and r['seed']==seed)
            report['P_cycle_comparisons'].append(dict(reset_mode=mode,seed=seed,baseline_cycles=old['cycles'],
                candidate_cycles=new['cycles'],saved_cycles=old['cycles']-new['cycles'],speedup=old['cycles']/new['cycles']))
        report['functional_passed']=True

        yosys=a.yosys or (Path(shutil.which('yosys')) if shutil.which('yosys') else None)
        if yosys is None or not yosys.is_file() or not a.liberty.is_file():
            report['mapped_area']=dict(status='not_executed',reason='Yosys or Nangate45 Liberty unavailable',
                                      yosys=str(yosys),liberty=str(a.liberty))
        else:
            _,version=execute([yosys,'-V'],a.out/'yosys-version.log')
            report['versions']['yosys']=version.strip()
            area=dict(status='passed',liberty=str(a.liberty),liberty_sha256=sha(a.liberty),
                      yosys_binary_sha256=sha(yosys),scope='technology-mapped paired-link synthesis only; no placement, routing, STA or mm2 claim',variants={})
            for variant in ('baseline','candidate'):
                directory=a.out/('synth-'+variant);directory.mkdir()
                candidate=variant=='candidate';module='pj_feed_elastic' if candidate else 'pj_feed_hold'
                wrapper='module pair_links(input wire clk,reset,input wire [1:0] src_valid,dst_ready,output wire [1:0] src_ready,dst_valid,empty,input wire [651:0] src_data,output wire [651:0] dst_data);\n'
                for i,(width,offset) in enumerate(((135,0),(517,135))):
                    wrapper+=f'{module} #(.WIDTH({width})) q{i}(.clk(clk),.reset(reset),.src_valid(src_valid[{i}]),.src_ready(src_ready[{i}]),.src_data(src_data[{offset}+:{width}]),.dst_valid(dst_valid[{i}]),.dst_ready(dst_ready[{i}]),.dst_data(dst_data[{offset}+:{width}])'
                    wrapper+=f',.empty(empty[{i}]));\n' if candidate else f');\nassign empty[{i}]=!dst_valid[{i}];\n'
                wrapper+='endmodule\n';top=directory/'pair_links.sv';top.write_bytes(wrapper.encode())
                hold=staged/variant/('pj_feed_elastic.sv' if candidate else 'pj_feed_hold.sv')
                def quote(path):return '"'+str(path).replace('\\','/').replace('"','\\"')+'"'
                script='\n'.join([
                    'read_liberty -lib '+quote(a.liberty),
                    'read_verilog -sv '+quote(hold)+' '+quote(top),
                    'hierarchy -check -top pair_links','proc; flatten; opt; memory_map; opt; techmap; opt',
                    'dfflibmap -liberty '+quote(a.liberty),'abc -liberty '+quote(a.liberty),'clean',
                    'tee -o '+quote(directory/'stat.json')+' stat -json -liberty '+quote(a.liberty),
                    'write_verilog -noattr '+quote(directory/'mapped.v')])+'\n'
                flow=directory/'synth.ys';flow.write_bytes(script.encode())
                execute([yosys,'-Q','-s',flow],directory/'synthesis.log')
                stats=json.loads((directory/'stat.json').read_text())
                module_stats=next(v for k,v in stats['modules'].items() if k.lstrip(chr(92))=='pair_links')
                area['variants'][variant]=dict(area_liberty_units=module_stats.get('area',stats.get('design',{}).get('area')),
                    num_cells=module_stats['num_cells'],cell_types=module_stats['num_cells_by_type'],
                    stat_sha256=sha(directory/'stat.json'),netlist_sha256=sha(directory/'mapped.v'))
            old_area=area['variants']['baseline']['area_liberty_units'];new_area=area['variants']['candidate']['area_liberty_units']
            if old_area is not None and new_area is not None:area['area_ratio']=new_area/old_area
            report['mapped_area']=area
        report['passed']=True
    except Exception as error:
        report['error']=type(error).__name__+': '+str(error)
        raise
    finally:
        report['output_files_sha256']={str(p.relative_to(a.out)):sha(p) for p in sorted(a.out.rglob('*'))
            if p.is_file() and p.name!='result.json' and p.suffix in ('.log','.json','.sv','.ys') and not any(part.startswith('obj-') for part in p.relative_to(a.out).parts)}
        (a.out/'result.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
        print(json.dumps(dict(passed=report['passed'],result=str(a.out/'result.json'),error=report.get('error'))),flush=True)


if __name__=='__main__':main()
