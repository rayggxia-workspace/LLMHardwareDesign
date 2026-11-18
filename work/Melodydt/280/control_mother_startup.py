"""Capture boot and initial native fetch using the frozen C639 executable model.

Counts are sampled C639 transactions, not seven-model extrapolated totals.
Core power replaces a core reference; it must never be added a second time.
"""
from pathlib import Path
import re
import shutil
import subprocess
import sys
from control_gap_calibration import LIB, PLATFORM, COHORT, sha, save, run, header, change, synth, boundary, power, constants


def requests(raw,scope):
    names=['clk_i','pm_req_valid_o','pm_req_ready_i','pm_req_write_o','pm_req_address_o','trace_pm_owner_o']
    with raw.open() as f:
        h=header(f);ids={n:h[scope+'/'+n][0] for n in names}
        values={};pending={};rows=[];now=None
        def flush(t):
            # Inspect pre-edge values. The FST dump is after RTL evaluation.
            before=values.get(ids['clk_i'],'0');after=pending.get(ids['clk_i'],before)
            if before=='0' and after=='1' and all(i in values for i in ids.values()):
                v={n:int(values[i],2) for n,i in ids.items()}
                if v['pm_req_valid_o'] and v['pm_req_ready_i']:
                    rows.append({'time_ps':t,'write':v['pm_req_write_o'],'address':v['pm_req_address_o'],'owner':v['trace_pm_owner_o']})
            values.update(pending);pending.clear()
        for line in f:
            if line.startswith('#'):
                if now is not None:flush(now)
                now=int(line[1:])
            else:
                c=change(line)
                if c and c[0] in ids.values():pending[c[0]]=c[1]
        if now is not None:flush(now)
    totals={}
    for row in rows:
        key='owner_%d_%s'%(row['owner'],'write' if row['write'] else 'read')
        totals[key]=totals.get(key,0)+1
    if not rows:raise ValueError('no mother PM traffic')
    return {'transactions':rows,'counts':totals,'sampling':'pre-edge ready/valid; owner codes require RTL interpretation'}


def main():
    bundle,out=map(Path,sys.argv[1:3]);job=sys.argv[3];cores=sys.argv[4]
    r=Path('/public/home/yuzelu/Melodydt/runs/issue-280');out.mkdir()
    ref=r/'c639-g32-gate-01/c639-g32-116937';sample=r/'c639-g32-active-01/active-116950'
    obj=ref/'replay-116937/obj';top='test_native_decode638_product_replay'
    shutil.copytree(sample/'source',out/'source')
    for name in ('source.tar','activity-0.txt','activity-1.txt','link.sh'):shutil.copy2(sample/name,out/name)
    driver=(sample/'g32_active.cpp').read_text()
    replacements={'constexpr uint64_t duration = 81920000;':'constexpr uint64_t duration = 500000000;',
                  'now >= first_call && accepted':'now >= 10000',
                  '            if (now >= first_down || duration > first_down - now) return 2;\n':'',
                  ' || accepts < 2':'', 'ffn-g32-active':'mother-startup', 'G32_ACTIVE':'MOTHER_STARTUP',
                  'G32_FIRST_ACCEPT':'MOTHER_CAPTURE_START'}
    for old,new in replacements.items():
        if driver.count(old)!=1:raise ValueError('capture driver changed: '+old)
        driver=driver.replace(old,new)
    (out/'g32_active.cpp').write_text(driver)
    runner=out/'source/project/experiments/block_local_native/run_decode638_q_tile_replay.sh'
    s=runner.read_text();assert s.count("grep '^G32_ACTIVE '")==1
    runner.write_text(s.replace("grep '^G32_ACTIVE '","grep '^MOTHER_STARTUP '"))
    run(['bash',str(out/'link.sh'),str(out),str(obj),top],out/'link.log')
    import os
    os.environ.update(SLURM_JOB_ID=job,SLURM_CPUS_PER_TASK=cores,FORCE_SECOND_FFN_REARM='1')
    run(['bash',str(runner),str(out),'/public/home/yuzelu/project-circuit/issue260-token-decode638-live-qkv-xWSJhdWQ/linked-103952',
         'history-final-product-ffn-repeat','636','2'],out/'replay.log')
    replay=out/('replay-'+job)
    absent_before_window=[]
    for mode in range(2):
        for name in ('transactions.tsv','write-transactions.tsv','activation-transactions.tsv'):
            original_path=ref/('replay-116937/DDR-%d'%mode)/name
            captured_path=replay/('DDR-%d'%mode)/name
            if not captured_path.exists():
                # Activation logs are created lazily, long after this boot
                # window. Prove the original has no admission in this window.
                if name!='activation-transactions.tsv':raise ValueError('missing transaction log '+name)
                first=min(int(line.split()[1]) for line in original_path.read_text().splitlines() if line.startswith('admit\t'))
                if first*10000<=500010000:raise ValueError('missing in-window activation traffic')
                absent_before_window.append({'mode':mode,'file':name,'first_frozen_admit_core_cycle':first,
                                             'capture_end_ps':500010000,'reference_sha256':sha(original_path)})
                continue
            with original_path.open('rb') as original,captured_path.open('rb') as captured:
                for block in iter(lambda:captured.read(1024*1024),b''):
                    if block!=original.read(len(block)):raise ValueError('DDR prefix mismatch '+name)
    converter_source=r/'c639-g32-power-03/power-116943/fst_scope_vcd.c'
    s=converter_source.read_text();old='fstReaderGetEndTime(reader) - fstReaderGetStartTime(reader) != 81920000'
    assert s.count(old)==1;s=s.replace(old,'fstReaderGetEndTime(reader) <= fstReaderGetStartTime(reader)')
    (out/'fst_scope_vcd.c').write_text(s)
    fstlib=Path('/public/home/yuzelu/opt/eda/verilator-5.042/share/verilator/include/gtkwave')
    run(['gcc','-std=gnu11','-O2','-D_GNU_SOURCE','-I'+str(fstlib),'-include',str(fstlib/'fst_config.h'),str(out/'fst_scope_vcd.c')]+
        [str(fstlib/(n+'.c')) for n in ('fstapi','fastlz','lz4')]+['-lz','-o',str(out/'fst_scope_vcd')],out/'converter-build.log')
    scope=COHORT+'/mother/mother/core';waves={}
    for mode in range(2):
        wave=replay/('DDR-%d/mother-startup.fst'%mode);raw=out/('mode-%d.vcd'%mode)
        run([str(out/'fst_scope_vcd'),str(wave),str(raw),scope],out/('extract-%d.log'%mode))
        waves[mode]=(wave,raw)
        save(out/('pm-requests-%d.json'%mode),requests(raw,scope))
    rtl=ref/'source/project/rtl/mother_control_native';source=rtl/'mc_native_controller.sv'
    s=source.read_text();forward='  wire return_fire=return_accept && return_validated;';driver='  wire return_validated='
    assert s.count(forward)==s.count(driver)==1
    s=s.replace(forward,'  wire return_validated;\n'+forward).replace(driver,'  assign return_validated=')
    (out/source.name).write_text(s)
    params=constants(waves[0][1],scope,['STALL_LIMIT','SERVICE_STALL_LIMIT','NATIVE_ABI_ID'])
    assert params==constants(waves[1][1],scope,list(params))
    design=synth(out/source.name,'mc_native_controller',params,out,rtl)
    rows={}
    for mode,(fst,raw) in waves.items():
        p=out/('mode-%d-power'%mode);p.mkdir();wave=p/'ports-300.vcd'
        timing=boundary(raw,wave,design,scope,{},'clk_i')
        tcl='\n'.join(['read_liberty {'+str(LIB)+'}',
              'read_lef {'+str(PLATFORM/'lef/NangateOpenCellLibrary.tech.lef')+'}',
              'read_lef {'+str(PLATFORM/'lef/NangateOpenCellLibrary.macro.mod.lef')+'}',
              'read_verilog {'+str(out/'mapped.v')+'}','link_design mc_native_controller',
              'create_clock -name core -period 3.333333333333 [get_ports clk_i]',
              'set_input_transition 0.05 [all_inputs]','read_vcd -scope dut {'+str(wave)+'}',
              'report_activity_annotation','report_power -digits 9'])+'\n'
        row=power(tcl,p,timing['port_bits']);row.update(timing)
        row.update(source_fst_sha256=sha(fst),wave_sha256=sha(wave),pm_counts=requests(raw,scope)['counts'])
        rows[str(mode)]=row
    save(out/'calibration.json',{'kind':'mother_startup_and_initial_fetch','clock_mhz':300,'wire_parasitics_loaded':False,
        'timing_signoff':False,'activity':'RTL boundary propagated, not internal gate replay','windows':rows,'parameters':params,
        'cell_count':len(design['cells']),'netlist_sha256':sha(out/'mapped.v'),
        'input_sha256':{str(p):sha(p) for p in [source,rtl/'mc_native_ports.svh',rtl/'native_instruction_fetch.svh',LIB,Path(__file__),bundle/'control_gap_calibration.py',out/'reused-model.sha256',runner]},
        'integration_status':'sampled boot core must replace existing core baseline; PM runtime reads need matching macro coefficient and model counts',
        'ddr_prefix_validation':'both modes match frozen transaction prefixes',
        'absent_activation_logs_before_first_admission':absent_before_window})
    print('CONTROL_MOTHER_STARTUP_PASS',flush=True)


if __name__=='__main__':main()
