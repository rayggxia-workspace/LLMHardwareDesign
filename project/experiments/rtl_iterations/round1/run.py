"""Actual integrated-U RTL arithmetic, compatibility and timing calibration."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import traceback

from generate import generate,sha,HERE,BASE_U_SHA,UPSTREAM_COMMIT

BANK=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v')
BANK_SHA='6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7'
VERILATOR=Path('/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator')
RTL_PATHS=[
 'project/rtl/block_local_s/block_local_s_arbiter.sv',
 'project/rtl/s_sram/local_s_base.sv','project/rtl/s_sram/block_feed_s16k_sram.sv',
 'project/rtl/block_v2/block_v2_n.sv','project/rtl/block_v2/block_v2_n_group.sv',
 'project/rtl/block_v2/block_v2_n_exp.svh','project/rtl/block_v2/block_v2_e.sv','project/rtl/block_v2/block_v2_e_compact.sv',
 'project/rtl/pu_leaf_base/pu_u_group.sv','project/rtl/pu_leaf_base/ucf_s_compute_client.sv',
 'project/rtl/pu_leaf_base/pu_compact_e_service.sv','project/rtl/pu_leaf_base/pu_u_direct_pair.sv',
 'project/rtl/pu_leaf_base/pu_nexp_shared.sv','project/rtl/pu_leaf_base/nexp_batch_adapter.sv']


def measurements(text,prefix):
    out=[]
    for line in text.splitlines():
        if line.startswith(prefix+' '):
            row={name:int(value) for name,value in re.findall(r'(\w+)=(-?\d+)',line)}
            out.append(row)
    return out


def ordinary_N(events):
    pending=None;out=[]
    for line in events:
        command=re.fullmatch(r'COMPAT CMD c=(\d+) lane=1 meta=([0-9a-fA-F]+) (.*)',line)
        done=re.fullmatch(r'COMPAT DONE c=(\d+) lane=1 (.*)',line)
        if command:
            if pending is not None:raise ValueError('overlapping normal N trace')
            pending=(int(command[1]),int(command[2],16),command[2]+' '+command[3])
        elif done:
            if pending is None:raise ValueError('unowned N completion')
            if pending[1]&15!=15:out.append((pending[2],int(done[1])-pending[0],done[2]))
            pending=None
    if pending is not None or not out:raise ValueError('incomplete ordinary N regression trace')
    return out


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    root=a.root.resolve();repo=root/'source';out=root/'results'
    cpus=int(os.environ.get('SLURM_CPUS_PER_TASK','0'))
    if not os.environ.get('SLURM_JOB_ID') or not 1<=cpus<=4:raise ValueError('actual Slurm allocation max4cores required')
    manifest=json.loads((root/'inputs.json').read_text(encoding='utf-8'))
    if not re.fullmatch('[0-9a-f]{40}',manifest.get('source_commit','')):raise ValueError('real source commit required')
    for field,base in (('code_sha256',repo),('input_sha256',root)):
        for name,digest in manifest.get(field,{}).items():
            if sha(base/name)!=digest:raise ValueError('deployment SHA drift '+name)
    if sha(BANK)!=BANK_SHA:raise ValueError('actual SRAM bank drift')
    out.mkdir(exist_ok=False)
    report=dict(passed=False,source_commit=manifest['source_commit'],manifest_sha256=sha(root/'inputs.json'),
        scope='Actual integrated production U optional NExp adapter, same single native N and16KiB S; no physical qualification',
        upstream_commit=UPSTREAM_COMMIT,baseline_U_sha256=BASE_U_SHA,
        rtl_source_sha256={name:sha(repo/name) for name in RTL_PATHS},bank_sha256=BANK_SHA,
        commands=[],runs=[],measurements=dict(compute_s16=[],compute_s32=[],full_U=[]),
        gates=dict(compute_s32=False,full_U=False,numeric=False,lifecycle=False,default_compatibility=False,enabled_ordinary=False),
        versions=dict(python=platform.python_version(),verilator=subprocess.check_output([VERILATOR,'--version'],text=True).strip(),
                      gcc=subprocess.check_output(['g++','--version'],text=True).splitlines()[0]),
        physical_qualified=False,native_N_instances=1)
    def save():(out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    def call(command,log):
        command=[str(c) for c in command]
        with (out/log).open('w',encoding='utf-8') as stream:
            r=subprocess.run(command,cwd=repo,stdout=stream,stderr=subprocess.STDOUT)
        record=dict(command=command,log=log,exit_code=r.returncode,log_sha256=sha(out/log));report['commands'].append(record)
        if r.returncode:raise RuntimeError('RTL command failed '+log)
        return (out/log).read_text(encoding='utf-8'),record
    try:
        g=out/'generated';report['generation']=generate(repo,g,integrated=True)
        r=repo/'project/rtl';u=r/'pu_leaf_base';n=r/'block_v2'
        compute_src=[u/'pu_nexp_shared.sv',u/'nexp_batch_adapter.sv',n/'block_v2_n.sv',n/'block_v2_n_group.sv']
        common=[r/'block_local_s/block_local_s_arbiter.sv',r/'s_sram/local_s_base.sv',r/'s_sram/block_feed_s16k_sram.sv',
                n/'block_v2_n.sv',n/'block_v2_n_group.sv',n/'block_v2_e.sv',n/'block_v2_e_compact.sv',
                u/'ucf_s_compute_client.sv',u/'pu_compact_e_service.sv',u/'pu_u_direct_pair.sv',BANK]
        extra=[u/'pu_nexp_shared.sv',u/'nexp_batch_adapter.sv']
        # Strict warning gate on newly authored synthesizable shared router.
        call([VERILATOR,'--lint-only','-Wall','--top-module','pu_nexp_shared',u/'pu_nexp_shared.sv',u/'nexp_batch_adapter.sv'],'new-router-lint.log')
        jobs=[('legacy','tb_pu_u_group',g/'tb_legacy.sv',[g/'pu_u_group_baseline.sv',*common]),
              ('default','tb_pu_u_group',g/'tb_legacy.sv',[u/'pu_u_group.sv',*common,*extra]),
              ('enabled_legacy','tb_pu_u_group',g/'tb_enabled_legacy.sv',[u/'pu_u_group.sv',*common,*extra]),
              ('compute','tb_nexp_compute',g/'tb_nexp_compute.sv',compute_src),
              ('full_U','tb_nexp_u',g/'tb_nexp_u.sv',[u/'pu_u_group.sv',*common,*extra])]
        signatures={}
        for label,top,bench,sources in jobs:
            obj=out/('obj-'+label)
            # Existing full native N/E/S sources and benches retain their
            # original warning policy; new synthesizable router passed strict lint.
            call([VERILATOR,'--binary','--timing','--assert','--timescale','1ns/1ps','-Wall','-Wno-fatal',
                  '--x-initial','unique','--x-assign','unique','-j',cpus,'-I'+str(n),'--top-module',top,'--Mdir',obj,bench,*sources],label+'-build.log')
            for mode,seed in ((1,143),(2,143),(2,144)):
                log=f'{label}-{mode}-{seed}.log';text,command=call([obj/('V'+top),f'+verilator+rand+reset+{mode}',f'+verilator+seed+{seed}'],log)
                row=dict(label=label,mode=mode,seed=seed,passed=True,log=log,log_sha256=command['log_sha256'],command=command['command'])
                if label in ('legacy','default','enabled_legacy'):
                    if 'PASS' not in text or 'FAIL' in text or '%Error' in text:raise ValueError('legacy RTL regression failed '+log)
                    events=[s for s in text.splitlines() if s.startswith('COMPAT ')]
                    if not events:raise ValueError('missing compatibility event trace')
                    if label=='legacy':signatures[mode,seed]=events
                    elif label=='default':
                        if events!=signatures[mode,seed]:raise ValueError('default0 command/S/response cycles differ from original')
                    elif ordinary_N(events)!=ordinary_N(signatures[mode,seed]):
                        raise ValueError('enabled ordinary N op0..14 cycles/response differ from original')
                    row['compatibility_events']=len(events)
                    row['normal_N_commands']=len(ordinary_N(events))
                    row['compatibility_sha256']=hashlib.sha256(('\n'.join(events)+'\n').encode()).hexdigest()
                elif label=='compute':
                    passed=measurements(text,'NEXP_COMPUTE_PASS')
                    if len(passed)!=1 or passed[0]['values']<65536:raise ValueError('incomplete numerical compute proof')
                    row['checks']=passed[0]
                    ms=measurements(text,'NEXP_COMPUTE')
                    if len(ms)!=12 or {(m['mode32'],m['count']) for m in ms}!={(0,n) for n in range(1,9)}|{(1,n) for n in range(1,5)}:
                        raise ValueError('missing/duplicate compute calibration rows')
                    for m in ms:
                        if m['accepted_to_next_accept_cycles']<=m['accepted_to_done_cycles']:raise ValueError('invalid compute handshake interval')
                        m.update(passed=True,mode=mode,seed=seed,log=log,log_sha256=command['log_sha256'],command=command['command'])
                        report['measurements']['compute_s32' if m['mode32'] else 'compute_s16'].append(m)
                else:
                    if 'NEXP_U_PASS ' not in text:raise ValueError('full integrated U proof missing')
                    ms=measurements(text,'NEXP_FULL_U')
                    if len(ms)!=12 or {(m['mode32'],m['count']) for m in ms}!={(0,n) for n in range(1,9)}|{(1,n) for n in range(1,5)}:
                        raise ValueError('missing/duplicate full-U calibration rows')
                    for m in ms:
                        if (m['S_reads']!=1 or m['S_writes']!=1 or m['accepted_to_done_cycles']!=
                            m['input_stage_cycles']+m['compute_stage_cycles']+m['output_stage_cycles']):raise ValueError('fullU S/compute stage conservation')
                        m.update(passed=True,mode=mode,seed=seed,log=log,log_sha256=command['log_sha256'],command=command['command'])
                        report['measurements']['full_U'].append(m)
                report['runs'].append(row);save()
        costs={}
        for count in range(1,5):
            observed={m['accepted_to_next_accept_cycles'] for m in report['measurements']['compute_s32'] if m['count']==count}
            if len(observed)!=1:raise ValueError('compute profile varies across initialization '+str(count))
            costs[count]=observed.pop()
        report['profile']=dict(schema_version=1,passed=True,
            scope='NExp supplemental compute wrapper service only; old vector_region unchanged',
            payload_contract='signed low16 of each S32 container, U16 zeroextend to S32',
            fallback_input_bits=[16],rows=[])
        for count in range(1,9):
            subcounts=[count] if count<=4 else [4,count-4]
            report['profile']['rows'].append(dict(count=count,charge_cycles=sum(costs[nn] for nn in subcounts),
                subcounts=subcounts,mode='legacy_s32_low16_zeroextend',
                derivation='sum of actual compute_s32 accepted_to_next_accept_cycles; one real128bit S32 frame holds at most4values; excludes private-S stages'))
        report['gates']={name:True for name in report['gates']};report['passed']=True
    except Exception as error:
        report['error']=repr(error);report['traceback']=traceback.format_exc();raise
    finally:save()
    print('ROUND1_INTEGRATED_U_PASS',flush=True)


if __name__=='__main__':main()
