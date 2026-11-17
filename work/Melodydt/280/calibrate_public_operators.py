"""Real public arithmetic RTL replay and paired boundary-propagated power."""
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys
from calibrate_rms_n import clip_ports


def digest(path): return sha256(path.read_bytes()).hexdigest()


def packed(values):
    if len(values)!=4 or any(not -2**31<=v<2**32 for v in values):
        raise ValueError('invalid four-lane operand')
    return '{:032x}'.format(sum((int(v)&0xffffffff)<<(32*i) for i,v in enumerate(values)))


def vectors(sample, kind):
    if kind in ('scan','apply'):
        words=sample['words'];count=words*4
        if kind=='scan':
            return ['{} {} {}'.format(count,-sample['shift'],sample['extra'])]+[
                packed(sample['source'][i:i+4]) for i in range(0,count,4)],count
        if words>512: raise ValueError('apply requires disjoint windows inside one S128 bank')
        fs=(13+sample['extra'] if sample['shifted_format'] else 13)-sample['shift']
        rows=['{} {} {} {}'.format(words,sample['factor'],fs,17+sample['output_shift'])]
        for i in range(0,count,4):
            rows.append(' '.join(packed(sample[k][i:i+4]) for k in ('source','gamma','expected')))
        return rows,count
    a,o,shape=sample['inputs'],sample['outputs'],sample['shape']
    if kind=='softmax':
        count=len(a['scores']); rows=[str(count)]
        data=[a['scores'],o['exponents'],o['probabilities']]
        if any(len(x)!=count for x in data): raise ValueError('softmax lengths differ')
        for i in range(0,count,4):
            rows.append(' '.join(packed(x[i:i+4]+[0]*max(0,i+4-count)) for x in data))
        return rows,count
    rows=[]
    if sample['kind']=='rope_native':
        packets=[(int(shape['negative']),shape['shifts'],a['value'],a['pair'],a['cos'],a['sin'],o['result'])]
    else:
        width=shape['width'];half=width//2;packets=[]
        if width%8: raise ValueError('unaligned RoPE pair')
        for i in range(0,width,4):
            pair=i+half if i<half else i-half
            packets.append((int(i<half),[14,0,0,14,0,0],a['value'][i:i+4],a['value'][pair:pair+4],
                            a['cos'][i:i+4],a['sin'][i:i+4],o['result'][i:i+4]))
    for negative,shifts,x,p,c,s,y in packets:
        rows.append(' '.join(map(str,[negative]+shifts))+' '+' '.join(packed(v) for v in (x,p,c,s,y)))
    return [str(len(rows))]+rows,len(rows)


def mapped_design(path, top, sources, lib):
    receipt=json.loads((path/'receipt.json').read_text())
    if receipt['exit_code'] or receipt.get('unmapped'): raise ValueError('mapping failed')
    for p,h in receipt['inputs_sha256'].items():
        if digest(Path(p))!=h: raise ValueError('mapped source changed')
    for name in ('mapped.v','mapped.json'):
        if digest(path/name)!=receipt['outputs_sha256'][name]: raise ValueError('netlist changed')
    if digest(lib)!=receipt['liberty_sha256']: raise ValueError('liberty changed')
    named={Path(p).name:h for p,h in receipt['inputs_sha256'].items()}
    for p in sources:
        if digest(p)!=named.get(p.name): raise ValueError('RTL/netlist source mismatch: '+str(p))
    return dict(path=path,top=top,ports=json.loads((path/'mapped.json').read_text())['modules'][top]['ports'],
                netlist_sha256=digest(path/'mapped.v'))


def power(design, platform, lib, work, raw, tb, instance, start, end, idle):
    result={};ports=design['ports']
    for name,lo,hi in (('active',start,end),('idle',end,idle)):
        prefix=instance+'-'+name; wave=work/(prefix+'.vcd')
        clip_ports(raw,wave,ports,lo,hi,testbench=tb,time_divisor=1,instance=instance)
        script=work/(prefix+'.tcl')
        script.write_text('\n'.join(['read_liberty {'+str(lib)+'}',
            'read_lef {'+str(platform/'lef/NangateOpenCellLibrary.tech.lef')+'}',
            'read_lef {'+str(platform/'lef/NangateOpenCellLibrary.macro.mod.lef')+'}',
            'read_verilog {'+str(design['path']/'mapped.v')+'}','link_design '+design['top'],
            'create_clock -name core -period 3.334 [get_ports clk]','set_input_transition 0.05 [all_inputs]',
            'read_vcd -scope dut {'+str(wave)+'}','report_activity_annotation','report_power -digits 9'])+'\n')
        log=work/(prefix+'.log')
        with log.open('w') as stream:
            subprocess.run(['openroad','-no_init','-threads','4','-exit',str(script)],stdout=stream,stderr=subprocess.STDOUT,check=True)
        content=log.read_text()
        totals=re.findall(r'(?m)^Total\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)',content)
        annotations=re.findall(r'Annotated (\d+) pin activities\.',content)
        if len(totals)!=1 or len(annotations)!=1 or re.search(r'(?m)^(Error:|\[ERROR)',content) or 'problem parsing bus' in content:
            raise ValueError('invalid power report')
        expected=sum(len(p['bits']) for p in ports.values())
        if int(annotations[0])<expected: raise ValueError('incomplete boundary annotation')
        result[name]=dict(power_w=dict(zip(('internal','switching','leakage','total'),map(float,totals[0]))),
                          annotation_bits=int(annotations[0]),required_boundary_bits=expected,
                          vcd_sha256=digest(wave),log_sha256=digest(log))
    return dict(top=design['top'],netlist_sha256=design['netlist_sha256'],power=result,
                incremental_nj=(result['active']['power_w']['total']-result['idle']['power_w']['total'])*(end-start)/1000)


def main():
    root,bundle,out=map(Path,sys.argv[1:4]);kind=sys.argv[4];captures=list(map(Path,sys.argv[5:]));out.mkdir()
    if kind not in ('softmax','rope','scan','apply'): raise ValueError('unknown kind')
    platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45');lib=platform/'lib/NangateOpenCellLibrary_typical.lib'
    common=root/'common-arithmetic-01/rtl'; compact=root/'operator-capture-02/rtl'
    if kind=='softmax':
        sources=[common/'n_s32_softmax_s128.sv',common/'block_v2_n_group.sv']
        designs={'dut':mapped_design(root/'common-arithmetic-01/run-38828028/n_s32_softmax_s128',
                                    'n_s32_softmax_s128',sources+[common/'exp_q16_lut.svh'],lib)}
    else:
        top={'rope':'rope_e32_ap64','scan':'s32_rms_range_scan','apply':'s32_rms_apply_s128'}[kind]
        sources=[compact/(top+'.sv')]
        if kind!='scan':sources += [compact/'e_s32_ap64.sv',compact/'e_s32_native.sv']
        mapped=root/'operator-capture-02/map-38830194'
        designs={'dut':mapped_design(mapped/top,top,sources[:1],lib)}
        if kind!='scan':designs['provider']=mapped_design(mapped/'e_s32_ap64','e_s32_ap64',sources[1:],lib)
    tb='tb_operator_'+kind; bench=bundle/(tb+'.sv');verilator=Path.home()/'LLMHardware/opt/verilator-5.042/bin/verilator'
    with (out/'build.log').open('w') as log:
        subprocess.run([str(verilator),'--binary','--timing','--trace','--trace-depth','2','-Wno-fatal','-j','12',
                        '--top-module',tb,'--Mdir',str(out/'obj'),'-I'+str(common)]+list(map(str,sources+[bench])),
                       stdout=log,stderr=subprocess.STDOUT,check=True)
    results=[];counts={};inputs={};excluded=[]
    for capture in captures:
        rms=kind in ('scan','apply')
        check=json.loads(capture.with_name('arithmetic-capture-check.json' if rms else 'operator-capture-check.json').read_text())
        if not check['passed'] or (not rms and check['capture_sha256']!=digest(capture)): raise ValueError('unaccepted capture')
        data=json.loads(capture.read_text());inputs[str(capture)]=digest(capture);counts[str(capture)]=data['rms_service_counts' if rms else 'counts']
        for index,sample in enumerate(data['samples']):
            if not rms and sample['kind'] not in ({'softmax'} if kind=='softmax' else {'rope','rope_native'}): continue
            if kind=='apply' and sample['words']>512:
                excluded.append(dict(capture=str(capture),sample_index=index,signature=sample['signature'],
                                     reason='activation+gamma exceed one 1024-word S128 bank; cross-bank/staging binding required'))
                continue
            work=out/('sample-%03d'%len(results));work.mkdir();rows,units=vectors(sample,kind)
            (work/'vectors.txt').write_text('\n'.join(rows)+'\n');raw=work/'rtl.vcd'
            run=subprocess.run([str(out/'obj'/('V'+tb)),'+vectors='+str(work/'vectors.txt'),'+wave='+str(raw)],capture_output=True,text=True)
            (work/'rtl.log').write_text(run.stdout+run.stderr);run.check_returncode()
            accepted=re.search(r'OPERATOR_PASS units=(\d+) cycles=(\d+)',run.stdout)
            activity=re.search(r'ACTIVITY_PASS active_start=(\d+) active_end=(\d+) idle_end=(\d+)',run.stdout)
            if not accepted or int(accepted[1])!=units or not activity: raise ValueError('RTL acceptance absent')
            start,end,idle=map(int,activity.groups())
            if end-start!=idle-end or end-start!=int(accepted[2])*3334: raise ValueError('window/cycle mismatch')
            components={instance:power(d,platform,lib,work,raw,tb,instance,start,end,idle) for instance,d in designs.items()}
            shape={k:sample[k] for k in ('words','shift','extra','output_shift')} if rms else sample['shape']
            result=dict(signature=sample['signature'],shape=shape,capture=str(capture),sample_index=index,
                        units=units,cycles=int(accepted[2]),window_ps=end-start,components=components,
                        incremental_nj=sum(x['incremental_nj'] for x in components.values()),
                        vectors_sha256=digest(work/'vectors.txt'),rtl_log_sha256=digest(work/'rtl.log'))
            (work/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');results.append(result)
            print('PUBLIC_OPERATOR_SAMPLE_PASS',kind,len(results),sample['signature'],flush=True)
    if not results: raise ValueError('no matching samples')
    report=dict(kind=kind,scope='sampled real operands; named arithmetic wrapper plus E32 where present; SRAM and system residency excluded; do not add provider E32 twice',
                activity='RTL boundary VCD propagated through mapped cells; no internal gate replay',
                memory_fixture='softmax/scan/apply use one-outstanding S128 fixture, not physical SRAM; apply uses disjoint X/Gamma windows in one bank',
                nominal_clock_mhz=300,period_ps=3334,wire_parasitics_loaded=False,timing_signoff=False,
                scheduler_latency_reconciled=False,source_commit=(bundle/'source-commit.txt').read_text().strip(),
                sources_sha256={str(p):digest(p) for p in sources+[bench]},liberty_sha256=digest(lib),inputs_sha256=inputs,
                verilator_version=subprocess.check_output([str(verilator),'--version'],text=True).strip(),
                openroad_version=subprocess.check_output(['openroad','-version'],text=True).strip(),
                captured_call_counts=counts,samples=results,excluded_samples=excluded)
    (out/'calibration.json').write_text(json.dumps(report,indent=2)+'\n');print('PUBLIC_OPERATOR_PASS',kind,len(results),flush=True)


if __name__=='__main__':main()
