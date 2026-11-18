"""Recalibrate mother runtime with captured parameters; audit sealed control pages.

Static page walking counts instructions/CALLs only. It does not simulate
provider execution, numeric results, time, or fabricate completion evidence.
"""
from collections import Counter
import json
from hashlib import sha256
from pathlib import Path
from struct import unpack_from, unpack
import sys
from zlib import crc32
from control_gap_calibration import LIB, PLATFORM, COHORT, sha, save, run, boundary, power


def mother(r,out):
    src=r/'control-expansion-20261118-01/mother-120304'
    receipt=json.loads((src/'calibration.json').read_text())
    assert receipt['parameters']['SERVICE_STALL_LIMIT'][1]==2000000
    design=json.loads((src/'mapped.json').read_text())['modules']['mc_native_controller']
    converter=r/'c639-g32-power-03/power-116943/fst_scope_vcd'
    scope=COHORT+'/mother/mother/core';rows={}
    for mode in range(2):
        for phase in ('gate-up','down','active'):
            p=out/('mode-%d-%s'%(mode,phase));p.mkdir()
            fst=(r/('c639-switch-active-300-01/result-117854/replay-117854/DDR-%d/switch-active.fst'%mode) if phase=='active'
                 else r/('c639-g32-gate-01/c639-g32-116937/replay-116937/DDR-%d/ffn-%s.fst'%(mode,phase)))
            raw=p/'raw.vcd';wave=p/'ports-300.vcd'
            run([str(converter),str(fst),str(raw),scope],p/'extract.log')
            timing=boundary(raw,wave,design,scope,{},'clk_i')
            tcl='\n'.join(['read_liberty {'+str(LIB)+'}',
                'read_lef {'+str(PLATFORM/'lef/NangateOpenCellLibrary.tech.lef')+'}',
                'read_lef {'+str(PLATFORM/'lef/NangateOpenCellLibrary.macro.mod.lef')+'}',
                'read_verilog {'+str(src/'mapped.v')+'}','link_design mc_native_controller',
                'create_clock -name core -period 3.333333333333 [get_ports clk_i]',
                'set_input_transition 0.05 [all_inputs]','read_vcd -scope dut {'+str(wave)+'}',
                'report_activity_annotation','report_power -digits 9'])+'\n'
            row=power(tcl,p,timing['port_bits']);row.update(timing)
            row.update(source_fst_sha256=sha(fst),wave_sha256=sha(wave));rows[p.name]=row
    return {'parameters':receipt['parameters'],'windows':rows,'clock_mhz':300,'wire_parasitics_loaded':False,
            'timing_signoff':False,'netlist_sha256':sha(src/'mapped.v'),'source_calibration_sha256':sha(src/'calibration.json'),
            'scope':'actual 2000000 service timeout core; replaces earlier 4096-parameter core reference'}


def page_counts(path,item):
    data=path.read_bytes();raw=data[:item['image_bytes']]
    if crc32(raw)!=item['crc']:raise ValueError('sealed page CRC mismatch '+str(path))
    pc=unpack_from('<I',raw,16)[0];count,offset=unpack_from('<II',raw,20)
    maximum=unpack_from('<I',raw,52)[0];entry=pc;regs=[0]*8;live={};ops=Counter();calls=[0]*4
    for step in range(maximum):
        if not 0<=pc<count:raise ValueError('PC out of bounds')
        imm,c,b,a,op=unpack('<IBBBB',raw[offset+pc*8:offset+(pc+1)*8]);ops[op]+=1
        if op==0x10:
            if a>=4 or b in live or a in live.values() or c or imm:raise ValueError('invalid CALL')
            live[b]=a;calls[a]+=1
        elif op==0x11:
            slots=[k for k in range(16) if imm & (1<<k)]
            if a or b or c or imm>>16 or not slots or any(k not in live for k in slots):raise ValueError('invalid WAIT')
            for k in slots:del live[k]
        elif op==0x13:
            if a>=8 or b or c:raise ValueError('invalid MOVI')
            regs[a]=imm
        elif op==0x16:
            if a not in (0,2,4,6) or b or c:raise ValueError('invalid ADDI64')
            n=regs[a]+(regs[a+1]<<32)+imm
            if n>=1<<64:raise ValueError('pointer overflow')
            regs[a],regs[a+1]=n&0xffffffff,n>>32
        elif op==0x17:
            if not 2<=a<8 or b or c or not entry<=imm<pc or not 0<regs[a]<=65535:raise ValueError('invalid LOOP')
            regs[a]-=1
            if regs[a]:pc=imm;continue
        elif op==0x1f:
            if a or b or c or imm or live:raise ValueError('invalid END')
            if sum(calls)!=item['count']:raise ValueError('descriptor count differs')
            return {'path':str(path),'sha256':sha(path),'calls_by_site':calls,'instructions':sum(ops.values()),
                    'opcodes':dict(ops),'bytes':item['image_bytes']}
        else:raise ValueError('unsupported opcode '+hex(op))
        pc+=1
    raise ValueError('step budget exceeded')


def counts(r,out,bundle):
    expected=json.loads((bundle/'control-count-input.json').read_text())
    older=r.parent/'issue-274'
    candidates=list((older/'three-p-full-01').glob('run-*/*/assets/plan.json'))
    candidates+=list((older/'three-p-gemma-q12-02').glob('run-*/*/assets/plan.json'))
    candidates+=list((r/'p0-ab-01').glob('ab-*/run-*/*/assets/plan.json'))
    candidates+=list(r.glob('ddr-pilot-*/pilot-*/staged/replay/run-*/*/assets/plan.json'))
    lookup={sha(p):p for p in candidates};rows={}
    for model,spec in expected.items():
        result={}
        for stage in ('prefill','decode'):
            key=spec[stage]['plan_sha256']
            binding='exact plan SHA'
            if key in lookup:path=lookup[key]
            elif model=='qwen3':
                # Qwen3 was recompiled into a relocated probe directory. Its
                # accepted original pilot is bound by the complete result,
                # excluding only the location-dependent plan SHA field.
                matched=[]
                for candidate in candidates:
                    if sha(candidate)!=spec[stage]['equivalent_original_plan_sha256']:continue
                    rp=candidate.parent.parent/'result.json'
                    if not rp.is_file():continue
                    result=json.loads(rp.read_text())
                    if result.pop('plan_sha256',None)!=sha(candidate):continue
                    digest=sha256(json.dumps(result,sort_keys=True,separators=(',',':')).encode()).hexdigest()
                    if digest==spec[stage]['full_result_without_plan_sha256']:matched.append(candidate)
                if len(matched)!=1:raise ValueError('original Qwen3 frozen pilot is not uniquely bound')
                path=matched[0];binding='original accepted pilot: full result identical except relocated plan SHA; current plan unavailable on old host'
            else:raise ValueError('frozen plan not found '+model+'/'+stage+' '+key)
            plan=json.loads(path.read_text())
            sealed={Path(v['path']).name:v['sha256'] for v in plan['images']}
            for phase in plan['phases']:
                name='prefill' if stage=='prefill' else ('first_token' if phase['position']==512 else 'decode')
                row=result.setdefault(name,{'instructions':0,'calls_by_site':[0]*4,'pages':[],'page_counts':Counter()})
                items=phase['ingress']+[p for layer in phase['layers'] for p in layer]
                if stage=='decode':items+=phase['head']
                for item in items:
                    if sha(path.parent/item['path'])!=sealed.get(item['path']):raise ValueError('plan image SHA differs '+item['path'])
                    counted=page_counts(path.parent/item['path'],item)
                    row['instructions']+=counted['instructions'];row['page_counts'][str(counted['bytes'])]+=1
                    row['calls_by_site']=[a+b for a,b in zip(row['calls_by_site'],counted['calls_by_site'])]
                    row['pages'].append(counted)
                row['plan_sha256']=sha(path);row['reported_plan_sha256']=key;row['plan_binding']=binding
        for name,row in result.items():
            ref=spec['windows'][name]
            if row['calls_by_site']!=ref['calls_by_site'] or dict(row['page_counts'])!=ref['page_counts']:
                raise ValueError('frozen TLM counters differ '+model+'/'+name+' '+str(row['calls_by_site'])+' '+str(ref))
            row['elapsed_ps']=ref['elapsed_ps'];row['tokens']=ref['tokens']
            row['control_packet_flits']=8*sum(row['calls_by_site'])
            row['flit_assumption']='successful four-flit CALL plus four-flit terminal; no cancel/retry traffic'
        rows[model]=result
    return {'models':rows,'input_sha256':sha(bundle/'control-count-input.json'),'script_sha256':sha(__file__),
            'scope':'static sealed control-page walk, reconciled to frozen TLM calls/pages; not timing or numeric replay',
            'runtime_pm_reads':'one accepted 128-bit PM fetch per executed compact instruction; no fetch cache in native RTL'}


if __name__=='__main__':
    bundle,out=map(Path,sys.argv[1:3]);out.mkdir()
    r=Path('/public/home/yuzelu/Melodydt/runs/issue-280')
    save(out/'mother-runtime.json',mother(r,out))
    save(out/'model-control-counts.json',counts(r,out,bundle))
    print('CONTROL_GAP_FOLLOWUP_PASS',flush=True)
